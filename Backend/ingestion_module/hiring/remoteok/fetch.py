"""
RemoteOK Jobs Parser
Fetches job listings from RemoteOK by parsing sitemap XML and scraping individual job pages.
Similar to Crunchboard module, but handles multiple job sitemaps.
"""

import copy
import re
import time
import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from lxml import etree, html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from services.request_headers import get_header
from utils.data_structures.hiring_data_structure import fetched_hiring_data as hiring_fetched_data

logger = logging.getLogger(__name__)

# URLs
SITEMAP_URL = "https://remoteok.com/sitemap.xml"
BASE_URL = "https://remoteok.com"

# Semaphore for rate limiting
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def parse_posted_date(date_str: str) -> Optional[datetime]:
    """
    Parse posted date from various formats.
    Examples: "2025-11-10", "2025-11-10T13:05:41+00:00", "Posted 3 days ago"
    """
    if not date_str:
        return None
    
    try:
        # Try ISO format first
        if 'T' in date_str:
            # ISO format: "2025-11-10T13:05:41+00:00"
            date_str = date_str.split('T')[0]
        
        # Try date format: "2025-11-10"
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
        
        # Try relative format: "Posted 3 days ago"
        match = re.search(r'posted\s+(\d+)\s+(day|days|month|months|week|weeks|hour|hours|minute|minutes)\s+ago', date_str.lower())
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            now = datetime.now()
            
            if 'day' in unit:
                return now - timedelta(days=number)
            elif 'month' in unit:
                return now - timedelta(days=number * 30)
            elif 'week' in unit:
                return now - timedelta(weeks=number)
            elif 'hour' in unit:
                return now - timedelta(hours=number)
            elif 'minute' in unit:
                return now - timedelta(minutes=number)
        
        return None
    except Exception as e:
        logger.debug(f"Error parsing date '{date_str}': {str(e)}")
        return None


def is_within_last_two_months(posted_date: Optional[datetime]) -> bool:
    """Check if a posted date is within the last two months."""
    if not posted_date:
        return False
    
    two_months_ago = datetime.now() - timedelta(days=60)
    return posted_date >= two_months_ago


async def fetch_sitemap_index(client: httpx.AsyncClient) -> Optional[str]:
    """Fetch the main sitemap index XML."""
    try:
        logger.info(f"Fetching sitemap index from {SITEMAP_URL}...")
        # Ensure we accept gzip encoding and get the decompressed content
        headers = get_header()
        headers['Accept-Encoding'] = 'gzip, deflate'
        response = await client.get(SITEMAP_URL, headers=headers, timeout=30.0)
        response.raise_for_status()
        
        # Try to get text, but if it's binary, decode it
        try:
            text = response.text
            # Check if it's actually XML
            if text.strip().startswith('<?xml') or '<sitemapindex' in text:
                return text
        except Exception as e:
            logger.debug(f"Failed to get text from response: {str(e)}")
        
        # If text didn't work, try decoding the content
        try:
            content = response.content
            # Try to detect if it's gzip compressed
            if content.startswith(b'\x1f\x8b'):  # Gzip magic number
                import gzip
                decompressed = gzip.decompress(content)
                text = decompressed.decode('utf-8')
                return text
            else:
                # Try UTF-8 decode
                text = content.decode('utf-8')
                return text
        except Exception as decode_error:
            logger.error(f"Error decoding sitemap response: {str(decode_error)}")
            return None
    except Exception as e:
        logger.error(f"Error fetching sitemap index: {str(e)}")
        return None


def extract_jobs_sitemap_urls(sitemap_xml: str) -> List[str]:
    """
    Extract all job sitemap URLs from the sitemap index.
    Returns a list of job sitemap URLs (e.g., sitemap-jobs-1.xml, sitemap-jobs-2.xml, etc.)
    """
    job_sitemap_urls = []
    
    try:
        root = etree.fromstring(sitemap_xml.encode())
        
        # Define namespaces
        namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Find all sitemap entries
        sitemaps = root.xpath('//sitemap:sitemap', namespaces=namespaces)
        
        for sitemap in sitemaps:
            loc_elem = sitemap.xpath('.//sitemap:loc', namespaces=namespaces)
            if loc_elem:
                url = loc_elem[0].text
                # Extract all job sitemaps (sitemap-jobs-*.xml)
                if 'sitemap-jobs-' in url:
                    logger.debug(f"Found job sitemap URL: {url}")
                    job_sitemap_urls.append(url)
        
        logger.info(f"Found {len(job_sitemap_urls)} job sitemap URLs")
        return job_sitemap_urls
    except Exception as e:
        logger.error(f"Error parsing sitemap index: {str(e)}")
        return []


async def fetch_jobs_sitemap(client: httpx.AsyncClient, jobs_sitemap_url: str) -> Optional[str]:
    """Fetch a specific jobs sitemap XML."""
    try:
        logger.debug(f"Fetching jobs sitemap from {jobs_sitemap_url}...")
        # Ensure we accept gzip encoding and get the decompressed content
        headers = get_header()
        headers['Accept-Encoding'] = 'gzip, deflate'
        response = await client.get(jobs_sitemap_url, headers=headers, timeout=30.0)
        response.raise_for_status()
        
        # Try to get text, but if it's binary, decode it
        try:
            text = response.text
            # Check if it's actually XML
            if text.strip().startswith('<?xml') or '<urlset' in text or '<url>' in text:
                return text
        except Exception as e:
            logger.error(f"Error reading response.text in fetch_jobs_sitemap: {str(e)}")
        
        # If text didn't work, try decoding the content
        try:
            content = response.content
            # Try to detect if it's gzip compressed
            if content.startswith(b'\x1f\x8b'):  # Gzip magic number
                import gzip
                decompressed = gzip.decompress(content)
                text = decompressed.decode('utf-8')
                return text
            else:
                # Try UTF-8 decode
                text = content.decode('utf-8')
                return text
        except Exception as decode_error:
            logger.error(f"Error decoding jobs sitemap response: {str(decode_error)}")
            return None
    except Exception as e:
        logger.error(f"Error fetching jobs sitemap {jobs_sitemap_url}: {str(e)}")
        return None


def extract_job_urls(jobs_sitemap_xml: str) -> List[Dict[str, Any]]:
    """Extract job URLs and metadata from a jobs sitemap."""
    jobs = []
    
    try:
        root = etree.fromstring(jobs_sitemap_xml.encode())
        
        # Define namespaces
        namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Find all URL entries
        urls = root.xpath('//sitemap:url', namespaces=namespaces)
        
        for url_elem in urls:
            try:
                # Extract location (URL)
                loc_elem = url_elem.xpath('.//sitemap:loc', namespaces=namespaces)
                if not loc_elem:
                    continue
                
                job_url = loc_elem[0].text
                
                # Skip base URL
                if job_url == BASE_URL or job_url == f"{BASE_URL}/":
                    continue
                
                # RemoteOK job URLs are like: /remote-jobs/remote-job-title-1128913
                # The job ID is at the end of the URL after a hyphen
                # Extract job ID from URL - look for numeric ID at the end
                job_id_match = re.search(r'-(\d+)$', job_url)
                if not job_id_match:
                    # Try alternative pattern: /remote-jobs/123456 or just /123456
                    job_id_match = re.search(r'/(\d+)(?:/|$)', job_url)
                    if not job_id_match:
                        # Skip if no numeric ID found (likely not a job URL)
                        continue
                
                # Extract lastmod (last modified date)
                lastmod_elem = url_elem.xpath('.//sitemap:lastmod', namespaces=namespaces)
                lastmod = lastmod_elem[0].text if lastmod_elem else None
                
                # Parse date
                posted_date = parse_posted_date(lastmod) if lastmod else None
                
                # Extract job ID from URL (already matched above)
                job_id = job_id_match.group(1)
                
                # Only process URLs that contain /remote-jobs/ (actual job postings)
                if '/remote-jobs/' not in job_url:
                    continue
                
                # Only include jobs from last 2 months
                if is_within_last_two_months(posted_date):
                    jobs.append({
                        "id": job_id,
                        "url": job_url,
                        "posted_date": lastmod,
                        "posted_datetime": posted_date
                    })
                else:
                    logger.debug(f"Skipping job {job_id} - posted date {lastmod} is older than 2 months")
            except Exception as e:
                logger.debug(f"Error parsing job URL entry: {str(e)}")
                continue
        
        logger.debug(f"Extracted {len(jobs)} job URLs from sitemap")
        return jobs
    except Exception as e:
        logger.error(f"Error parsing jobs sitemap: {str(e)}")
        return []


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance."""
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove webdriver property to avoid detection
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        return driver
    except Exception as e:
        logger.error(f"Error creating Chrome driver: {str(e)}")
        raise


async def fetch_page_with_selenium(url: str, wait_time: int = 10) -> Optional[str]:
    """Fetch a page using Selenium and return the HTML content after JavaScript execution."""
    loop = asyncio.get_event_loop()
    
    def _fetch():
        driver = None
        try:
            driver = create_driver(headless=True)
            driver.get(url)
            
            # Wait for page to load
            try:
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Additional wait for dynamic content
            except TimeoutException:
                logger.warning(f"Timeout waiting for page {url}, but continuing...")
                time.sleep(2)
            
            # Get page source after JavaScript execution
            html_content = driver.page_source
            return html_content
            
        except Exception as e:
            logger.error(f"Error fetching page with Selenium: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
        finally:
            if driver:
                driver.quit()
    
    if hasattr(asyncio, 'to_thread'):
        return await asyncio.to_thread(_fetch)
    else:
        return await loop.run_in_executor(None, _fetch)


async def fetch_job_page(client: httpx.AsyncClient, job_url: str) -> Optional[str]:
    """Fetch HTML content of a job page using Selenium."""
    async with semaphore:
        try:
            # Use Selenium to bypass potential protection
            html_content = await fetch_page_with_selenium(job_url, wait_time=10)
            return html_content
        except Exception as e:
            logger.debug(f"Error fetching job page {job_url}: {str(e)}")
            return None


def parse_job_page(html_content: str, job_id: str, job_url: str) -> Optional[Dict[str, Any]]:
    """Parse job information from HTML content."""
    if not html_content:
        return None
    
    try:
        tree = html.fromstring(html_content)
        
        # Extract job title (common selectors for RemoteOK)
        title = None
        title_selectors = [
            '//h1[@class="job-title"]',
            '//h1[contains(@class, "title")]',
            '//h1',
            '//div[@class="job-title"]//h1',
            '//title'
        ]
        for selector in title_selectors:
            title_elem = tree.xpath(selector)
            if title_elem:
                title = title_elem[0].text_content().strip()
                break
        
        # Extract company name
        company = None
        company_selectors = [
            '//div[@class="company"]',
            '//span[@class="company-name"]',
            '//a[@class="company"]',
            '//div[contains(@class, "company")]',
            '//h2[contains(@class, "company")]'
        ]
        for selector in company_selectors:
            company_elem = tree.xpath(selector)
            if company_elem:
                company = company_elem[0].text_content().strip()
                break
        
        # Extract description first (get all text content) - we'll use it to extract location
        description = None
        desc_selectors = [
            '//div[@class="job-description"]',
            '//div[@class="description"]',
            '//div[contains(@class, "description")]',
            '//div[@id="job-description"]',
            '//div[@class="content"]'
        ]
        for selector in desc_selectors:
            desc_elem = tree.xpath(selector)
            if desc_elem:
                description = desc_elem[0].text_content().strip()
                break
        
        # If no description found, try to get body text
        if not description:
            body_elem = tree.xpath('//body')
            if body_elem:
                description = body_elem[0].text_content().strip()[:2000]  # Limit length
        
        # Extract location - RemoteOK uses various formats
        location = None
        location_selectors = [
            # Common RemoteOK selectors
            '//span[contains(@class, "location")]',
            '//div[contains(@class, "location")]',
            '//span[@class="location"]',
            '//div[@class="location"]',
            # Try data attributes
            '//*[@data-location]',
            '//*[contains(@class, "tag") and contains(text(), "Remote")]',
            '//*[contains(@class, "tag") and contains(text(), "Worldwide")]',
            # Try to find location in job tags/badges
            '//span[contains(@class, "tag")]',
            '//div[contains(@class, "tag")]',
        ]
        for selector in location_selectors:
            try:
                location_elem = tree.xpath(selector)
                if location_elem:
                    loc_text = location_elem[0].text_content().strip() if hasattr(location_elem[0], 'text_content') else str(location_elem[0]).strip()
                    if loc_text and loc_text.lower() not in ['', 'n/a', 'none']:
                        location = loc_text
                        break
            except Exception:
                continue
        
        # If still no location, try to extract from description or title
        if not location or location == "N/A":
            # Check if description contains location info
            if description:
                # Look for common location patterns in description
                location_patterns = [
                    r'(?:based in|located in|from|in|headquartered in)\s+([A-Z][a-zA-Z\s,]+(?:,\s*[A-Z]{2})?)',
                    r'([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)\s+(?:based|located|headquartered)',
                    r'(?:office in|offices in)\s+([A-Z][a-zA-Z\s,]+(?:,\s*[A-Z]{2})?)',
                ]
                for pattern in location_patterns:
                    match = re.search(pattern, description, re.IGNORECASE)
                    if match:
                        location = match.group(1).strip()
                        break
            
            # If still no location, default to "Remote" for RemoteOK (since it's a remote job board)
            if not location or location == "N/A":
                location = "Remote"
        
        return {
            "id": job_id,
            "url": job_url,
            "title": title or "N/A",
            "company": company or "N/A",
            "location": location or "N/A",
            "description": description or ""
        }
    except Exception as e:
        logger.debug(f"Error parsing job page {job_url}: {str(e)}")
        return None


async def fetch_job_details_batch(client: httpx.AsyncClient, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch and parse job details for a batch of jobs."""
    tasks = []
    for job in jobs:
        task = fetch_job_page(client, job["url"])
        tasks.append((job, task))
    
    job_details = []
    for job, task in tasks:
        html_content = await task
        if html_content:
            parsed_job = parse_job_page(html_content, job["id"], job["url"])
            if parsed_job:
                # Merge with sitemap data
                parsed_job["posted_date"] = job.get("posted_date")
                parsed_job["posted_datetime"] = job.get("posted_datetime")
                job_details.append(parsed_job)
    
    return job_details


def extract_job_postings(jobs: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Extract and format job postings for AI extraction.
    Returns structured data with ids, urls, and titles.
    """
    logger.info(f"Extracting {len(jobs)} job postings...")
    
    job_postings = {
        "ids": [],
        "urls": [],
        "titles": []
    }
    
    for job in jobs:
        job_id = job.get("id", "")
        job_url = job.get("url", "")
        job_title = job.get("title", "N/A")
        job_company = job.get("company", "N/A")
        job_location = job.get("location", "N/A")
        job_description = job.get("description", "")
        
        # Format title for AI extraction: "Title | Company | Location | Description"
        # Include description so AI can extract city/country even if location is just "Remote"
        if job_description:
            # Truncate description to avoid making the prompt too long
            desc_snippet = job_description[:1000] if len(job_description) > 1000 else job_description
            formatted_title = f"{job_title} | {job_company} | {job_location} | Description: {desc_snippet}"
        else:
            formatted_title = f"{job_title} | {job_company} | {job_location}"
        
        job_postings["ids"].append(job_id)
        job_postings["urls"].append(job_url)
        job_postings["titles"].append(formatted_title)
    
    logger.info(f"Extracted {len(job_postings['ids'])} job postings for AI extraction")
    return job_postings


async def main():
    """
    Main function to fetch RemoteOK Jobs data.
    Follows the same pattern as other hiring modules:
    1. Fetch sitemap index
    2. Extract all job sitemap URLs
    3. Fetch each job sitemap
    4. Extract job URLs from all sitemaps
    5. Fetch and parse job pages
    6. Feed to AI extraction module
    7. Return structured data
    """
    start_time = time.perf_counter()
    logger.info("Starting RemoteOK Jobs data fetch...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Fetch sitemap index
            sitemap_xml = await fetch_sitemap_index(client)
            if not sitemap_xml:
                logger.error("Failed to fetch sitemap index")
                return {}
            
            # Step 2: Extract all job sitemap URLs
            job_sitemap_urls = extract_jobs_sitemap_urls(sitemap_xml)
            if not job_sitemap_urls:
                logger.error("Failed to find job sitemap URLs")
                return {}
            
            logger.info(f"Found {len(job_sitemap_urls)} job sitemaps to process")
            
            # Step 3: Fetch each job sitemap and extract job URLs
            all_job_urls = []
            for i, job_sitemap_url in enumerate(job_sitemap_urls, 1):
                logger.info(f"Processing job sitemap {i}/{len(job_sitemap_urls)}: {job_sitemap_url}")
                jobs_sitemap_xml = await fetch_jobs_sitemap(client, job_sitemap_url)
                if jobs_sitemap_xml:
                    job_urls = extract_job_urls(jobs_sitemap_xml)
                    all_job_urls.extend(job_urls)
                    logger.info(f"Extracted {len(job_urls)} jobs from sitemap {i} (total: {len(all_job_urls)})")
                else:
                    logger.warning(f"Failed to fetch job sitemap {i}: {job_sitemap_url}")
                
                # Small delay between sitemaps
                await asyncio.sleep(1)
            
            if not all_job_urls:
                logger.warning("No job URLs found from sitemaps")
                return {}
            
            logger.info(f"Found {len(all_job_urls)} job URLs from all sitemaps")
            
            # Step 4: Fetch and parse individual job pages in batches
            all_parsed_jobs = []
            batch_size = 10  # Process 10 jobs at a time
            for i in range(0, len(all_job_urls), batch_size):
                batch = all_job_urls[i:i + batch_size]
                logger.info(f"Fetching batch {int(i/batch_size) + 1} ({len(batch)} jobs)...")
                parsed_batch = await fetch_job_details_batch(client, batch)
                all_parsed_jobs.extend(parsed_batch)
                await asyncio.sleep(2)  # Small delay between batches
            
            if not all_parsed_jobs:
                logger.warning("No job listings found after parsing individual pages")
                return {}
            
            # Step 5: Extract job postings for AI extraction
            job_postings = extract_job_postings(all_parsed_jobs)
            
            if not job_postings["ids"]:
                logger.warning("No job postings extracted for AI processing")
                return {}
            
            # Step 6: Feed to AI extraction module
            logger.info(f"Feeding {len(job_postings['ids'])} job postings to AI extraction...")
            from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
            extracted_data = await finalize_ai_extraction(job_postings)
            
            # Step 7: Format results and summary
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            
            # Format results similar to other hiring modules
            result = copy.deepcopy(hiring_fetched_data)
            result["source"] = "RemoteOK"
            
            # Add extracted data
            for key, value in extracted_data.items():
                if key in result:
                    result[key].extend(value if isinstance(value, list) else [value])
            
            # Calculate summary statistics
            total_jobs = len(all_parsed_jobs)
            extracted_count = len(extracted_data.get("article_id", []))
            success_rate = (extracted_count / total_jobs * 100) if total_jobs > 0 else 0
            
            # Get unique companies, roles, cities, countries
            unique_companies = set(extracted_data.get("company_name", []))
            unique_roles = []
            for role_list in extracted_data.get("job_roles", []):
                if isinstance(role_list, list):
                    unique_roles.extend(role_list)
                else:
                    unique_roles.append(role_list)
            unique_roles = set(unique_roles)
            unique_cities = set(extracted_data.get("company_city", []))
            unique_countries = set(extracted_data.get("company_country", []))
            
            # Log summary
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"RemoteOK Jobs Data Fetch Summary")
            logger.info("=" * 80)
            logger.info(f"Total time: {elapsed_time:.2f} seconds")
            logger.info(f"Job URLs found: {total_jobs}")
            logger.info(f"Jobs extracted: {extracted_count}/{total_jobs} ({success_rate:.1f}% success rate)")
            logger.info(f"Unique companies: {len(unique_companies)}")
            logger.info(f"Unique job roles: {len(unique_roles)}")
            logger.info(f"Unique cities: {len(unique_cities)}")
            logger.info(f"Unique countries: {len(unique_countries)}")
            logger.info("")
            
            # Sample results
            if extracted_count > 0:
                logger.info("Sample results:")
                sample_size = min(3, extracted_count)
                for i in range(sample_size):
                    logger.info(f"  {i+1}. {extracted_data.get('article_title', [''])[i] if i < len(extracted_data.get('article_title', [])) else 'N/A'}")
                    logger.info(f"     Company: {extracted_data.get('company_name', [''])[i] if i < len(extracted_data.get('company_name', [])) else 'N/A'}")
                    logger.info(f"     Location: {extracted_data.get('company_city', [''])[i] if i < len(extracted_data.get('company_city', [])) else 'N/A'}, {extracted_data.get('company_country', [''])[i] if i < len(extracted_data.get('company_country', [])) else 'N/A'}")
                    logger.info("")
            
            logger.info("=" * 80)
            logger.info("")
            
            return result
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return {}


if __name__ == "__main__":
    asyncio.run(main())

