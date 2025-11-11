"""
Crunchboard Jobs Parser
Fetches job listings from Crunchboard by parsing sitemap XML and scraping individual job pages.
Similar to other hiring modules, this parses structured data and feeds it to AI extraction.
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
SITEMAP_URL = "https://www.crunchboard.com/sitemap.xml"
BASE_URL = "https://www.crunchboard.com"

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
        response = await client.get(SITEMAP_URL, headers=get_header(), timeout=30.0)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching sitemap index: {str(e)}")
        return None


def extract_jobs_sitemap_url(sitemap_xml: str) -> Optional[str]:
    """Extract the jobs sitemap URL from the sitemap index."""
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
                if 'jobs/job_sitemap_details.xml' in url:
                    logger.info(f"Found jobs sitemap URL: {url}")
                    return url
        
        logger.warning("Jobs sitemap URL not found in sitemap index")
        return None
    except Exception as e:
        logger.error(f"Error parsing sitemap index: {str(e)}")
        return None


async def fetch_jobs_sitemap(client: httpx.AsyncClient, jobs_sitemap_url: str) -> Optional[str]:
    """Fetch the jobs sitemap XML."""
    try:
        logger.info(f"Fetching jobs sitemap from {jobs_sitemap_url}...")
        response = await client.get(jobs_sitemap_url, headers=get_header(), timeout=30.0)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching jobs sitemap: {str(e)}")
        return None


def extract_job_urls(jobs_sitemap_xml: str) -> List[Dict[str, Any]]:
    """Extract job URLs and metadata from the jobs sitemap."""
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
                
                # Skip base URL (https://www.crunchboard.com)
                if job_url == "https://www.crunchboard.com" or job_url == BASE_URL:
                    continue
                
                # Only process URLs that contain /jobs/
                if '/jobs/' not in job_url:
                    continue
                
                # Extract lastmod (last modified date)
                lastmod_elem = url_elem.xpath('.//sitemap:lastmod', namespaces=namespaces)
                lastmod = lastmod_elem[0].text if lastmod_elem else None
                
                # Parse date
                posted_date = parse_posted_date(lastmod) if lastmod else None
                
                # Extract job ID from URL (e.g., /jobs/463195554-online-technical-support-specialist-at-the-climate-center -> 463195554)
                job_id_match = re.search(r'/jobs/(\d+)', job_url)
                job_id = job_id_match.group(1) if job_id_match else job_url.split('/')[-1].split('-')[0]
                
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
        
        logger.info(f"Extracted {len(jobs)} job URLs from sitemap")
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
            logger.debug(f"Loading page: {url}")
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
            # Use Selenium to bypass 403 protection
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
        
        # Extract job title (common selectors for job boards)
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
            '//div[contains(@class, "company")]'
        ]
        for selector in company_selectors:
            company_elem = tree.xpath(selector)
            if company_elem:
                company = company_elem[0].text_content().strip()
                break
        
        # Extract location
        location = None
        location_selectors = [
            '//div[@class="location"]',
            '//span[@class="location"]',
            '//div[contains(@class, "location")]'
        ]
        for selector in location_selectors:
            location_elem = tree.xpath(selector)
            if location_elem:
                location = location_elem[0].text_content().strip()
                break
        
        # Extract description (get all text content)
        description = None
        desc_selectors = [
            '//div[@class="job-description"]',
            '//div[@class="description"]',
            '//div[contains(@class, "description")]',
            '//div[@id="job-description"]'
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
        job_id = job.get("id")
        job_url = job.get("url")
        title = job.get("title", "")
        company = job.get("company", "")
        location = job.get("location", "")
        
        # Create a combined title with company and location for better AI extraction
        combined_title = f"{title} | {company} | {location}"
        
        job_postings["ids"].append(job_id)
        job_postings["urls"].append(job_url)
        job_postings["titles"].append(combined_title)
    
    logger.info(f"Extracted {len(job_postings['ids'])} job postings")
    return job_postings


async def main():
    """
    Main function to fetch Crunchboard Jobs data.
    Follows the same pattern as other hiring modules:
    1. Fetch sitemap index
    2. Extract jobs sitemap URL
    3. Fetch jobs sitemap
    4. Extract job URLs
    5. Fetch and parse job pages
    6. Feed to AI extraction module
    7. Return structured data
    """
    start_time = time.perf_counter()
    logger.info("Starting Crunchboard Jobs data fetch...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Fetch sitemap index
            sitemap_xml = await fetch_sitemap_index(client)
            if not sitemap_xml:
                logger.error("Failed to fetch sitemap index")
                return {}
            
            # Step 2: Extract jobs sitemap URL
            jobs_sitemap_url = extract_jobs_sitemap_url(sitemap_xml)
            if not jobs_sitemap_url:
                logger.error("Failed to find jobs sitemap URL")
                return {}
            
            # Step 3: Fetch jobs sitemap
            jobs_sitemap_xml = await fetch_jobs_sitemap(client, jobs_sitemap_url)
            if not jobs_sitemap_xml:
                logger.error("Failed to fetch jobs sitemap")
                return {}
            
            # Step 4: Extract job URLs
            job_urls = extract_job_urls(jobs_sitemap_xml)
            if not job_urls:
                logger.warning("No job URLs found in sitemap")
                return {}
            
            logger.info(f"Found {len(job_urls)} job URLs from sitemap")
            
            # Step 5: Fetch and parse job pages (in batches to avoid overwhelming the server)
            batch_size = 20
            all_jobs = []
            
            for i in range(0, len(job_urls), batch_size):
                batch = job_urls[i:i + batch_size]
                logger.info(f"Fetching batch {i // batch_size + 1} ({len(batch)} jobs)...")
                
                batch_jobs = await fetch_job_details_batch(client, batch)
                all_jobs.extend(batch_jobs)
                
                logger.info(f"Fetched {len(batch_jobs)} jobs from batch (total: {len(all_jobs)})")
                
                # Small delay between batches
                if i + batch_size < len(job_urls):
                    await asyncio.sleep(1)
            
            if not all_jobs:
                logger.warning("No job listings found")
                return {}
            
            # Step 6: Extract job postings for AI extraction
            job_postings = extract_job_postings(all_jobs)
            
            if not job_postings["ids"]:
                logger.warning("No job postings extracted")
                return {}
            
            # Step 7: Feed to AI extraction module
            logger.info(f"Feeding {len(job_postings['ids'])} job postings to AI extraction...")
            try:
                from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
                extracted_data = await finalize_ai_extraction(job_postings)
            except Exception as e:
                logger.error(f"Failed to extract AI content from Crunchboard data: {str(e)}")
                extracted_data = {}
            
            # Step 8: Format results
            llm_results = None
            if extracted_data:
                llm_results = copy.deepcopy(hiring_fetched_data)
                llm_results.update(extracted_data)
            
            # Step 9: Summary
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("CRUNCHBOARD JOBS EXTRACTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏱️  Total time: {elapsed_time:.2f} seconds ({elapsed_time / 60:.1f} minutes)")
            logger.info(f"📊 Input: {len(job_postings['ids'])} job postings processed")
            logger.info(f"✅ Successfully extracted: {len(extracted_data.get('ids', []))} job postings")
            logger.info("")
            
            if extracted_data:
                # Extract statistics
                companies = [c for c in extracted_data.get('company_name', []) if c]
                unique_companies = set(companies) if companies else set()
                
                # Flatten job_roles (it's a list of lists)
                job_roles = []
                for roles in extracted_data.get('job_roles', []):
                    if isinstance(roles, list):
                        job_roles.extend(roles)
                    elif roles:
                        job_roles.append(roles)
                unique_roles = set(job_roles) if job_roles else set()
                
                cities = [c for c in extracted_data.get('company_city', []) if c]
                unique_cities = set(cities) if cities else set()
                
                countries = [c for c in extracted_data.get('company_country', []) if c]
                unique_countries = set(countries) if countries else set()
                
                logger.info("📈 Extraction Statistics:")
                logger.info(f"   • Unique Companies: {len(unique_companies)}")
                logger.info(f"   • Unique Job Roles: {len(unique_roles)}")
                logger.info(f"   • Unique Cities: {len(unique_cities)}")
                logger.info(f"   • Unique Countries: {len(unique_countries)}")
                logger.info("")
                
                # Top companies
                if unique_companies:
                    logger.info("🏢 Top Companies:")
                    for company in list(unique_companies)[:5]:
                        count = companies.count(company)
                        logger.info(f"   • {company}: {count} posting(s)")
                    logger.info("")
                
                # Top job roles
                if unique_roles:
                    logger.info("💼 Top Job Roles:")
                    for role in list(unique_roles)[:5]:
                        count = job_roles.count(role)
                        logger.info(f"   • {role}: {count} posting(s)")
                    logger.info("")
                
                # Sample results
                sample_size = min(3, len(extracted_data.get('ids', [])))
                if sample_size > 0:
                    logger.info("📋 Sample Results (first 3):")
                    for i in range(sample_size):
                        job_id = extracted_data.get('ids', [])[i]
                        company = extracted_data.get('company_name', [])[i] if i < len(extracted_data.get('company_name', [])) else "N/A"
                        role = extracted_data.get('job_roles', [])[i] if i < len(extracted_data.get('job_roles', [])) else "N/A"
                        city = extracted_data.get('company_city', [])[i] if i < len(extracted_data.get('company_city', [])) else "N/A"
                        country = extracted_data.get('company_country', [])[i] if i < len(extracted_data.get('company_country', [])) else "N/A"
                        logger.info(f"   {i + 1}. ID: {job_id}")
                        logger.info(f"      Company: {company}")
                        logger.info(f"      Role: {role}")
                        logger.info(f"      Location: {city}, {country}")
                    logger.info("")
            
            logger.info("=" * 80)
            
            return llm_results or {}
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


if __name__ == "__main__":
    asyncio.run(main())

