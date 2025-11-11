"""
Stack Overflow Jobs Parser
Fetches job listings from Stack Overflow Jobs and extracts structured data.
Similar to Hacker News module, this parses HTML and feeds it to AI extraction.

NOTE: Stack Overflow Jobs is powered by Indeed and uses JavaScript-rendered content.
This module uses Selenium with a headless browser to execute JavaScript and bypass anti-bot protection.
"""

import copy
import re
import time
import asyncio
import logging
import json
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
from utils.data_structures.hiring_data_structure import fetched_hiring_data as hiring_fetched_data

logger = logging.getLogger(__name__)

# URLs
BASE_URL = "https://stackoverflowjobs.com"
JOBS_URL = "https://stackoverflowjobs.com"
JOBBOARD_CONFIG_URL = "https://stackoverflowjobs.com/jobboard-config"

# Semaphore for rate limiting
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def parse_posted_date(date_str: str) -> Optional[datetime]:
    """
    Parse posted date from Stack Overflow Jobs format.
    Examples: "Posted 3 months ago", "Posted 19 days ago", "Posted 5 days ago"
    """
    if not date_str:
        return None
    
    try:
        # Extract number and unit (use lowercase pattern since we're searching in lowercase string)
        match = re.search(r'posted\s+(\d+)\s+(day|days|month|months|week|weeks|hour|hours|minute|minutes)\s+ago', date_str.lower())
        if not match:
            return None
        
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


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance."""
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Install and use ChromeDriver
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


async def fetch_page_with_selenium(url: str, wait_time: int = 15) -> Optional[str]:
    """Fetch a page using Selenium and return the HTML content after JavaScript execution."""
    loop = asyncio.get_event_loop()
    
    def _fetch():
        driver = None
        try:
            driver = create_driver(headless=True)
            logger.debug(f"Loading page: {url}")
            driver.get(url)
            
            # Wait for job listings to load (look for job list container)
            try:
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.ID, "job-list"))
                )
                logger.debug("Job list container found, waiting for content...")
                time.sleep(2)  # Additional wait for dynamic content
            except TimeoutException:
                logger.warning("Job list container not found, but continuing...")
                time.sleep(3)  # Wait anyway for content to load
            
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


async def fetch_job_listings_page(page: int = 1, country: str = "US") -> Optional[str]:
    """
    Fetch a page of job listings from Stack Overflow Jobs using Selenium.
    Returns HTML content after JavaScript execution.
    """
    try:
        url = f"{JOBS_URL}/?co={country}"
        if page > 1:
            url += f"&c={10 * (page - 1)}"  # Stack Overflow uses 'c' parameter for offset
        
        logger.info(f"Fetching Stack Overflow Jobs page {page} with Selenium...")
        html_content = await fetch_page_with_selenium(url, wait_time=15)
        
        if not html_content:
            logger.error(f"Failed to fetch page {page}")
            return None
        
        # Check if we got actual content (not just the JS loader)
        if len(html_content) < 1000:
            logger.warning(f"Response seems too short ({len(html_content)} chars), might be JS loader")
            return None
        
        logger.info(f"Successfully fetched page {page} ({len(html_content)} chars)")
        return html_content
        
    except Exception as e:
        logger.error(f"Error fetching Stack Overflow Jobs page {page}: {str(e)}")
        return None


def parse_job_listings(html_content: str) -> List[Dict[str, Any]]:
    """
    Parse job listings from HTML content.
    Returns list of job dictionaries with id, title, company, location, etc.
    """
    if not html_content:
        return []
    
    try:
        # Parse HTML
        tree = html.fromstring(html_content)
        
        # Find all job listing items
        # Jobs are in <li> elements with class containing 'chakra-list__item'
        job_items = tree.xpath('//li[contains(@class, "chakra-list__item")]//div[@data-jobkey]')
        
        jobs = []
        
        for item in job_items:
            try:
                job_key = item.get('data-jobkey')
                if not job_key:
                    continue
                
                # Extract job title
                title_elem = item.xpath('.//h2[contains(@class, "css-1in8x96")]')
                title = title_elem[0].text_content().strip() if title_elem else "N/A"
                
                # Extract company name
                company_elem = item.xpath('.//p[contains(@class, "css-1pnk0le")]')
                company = company_elem[0].text_content().strip() if company_elem else "N/A"
                
                # Extract location
                location_elem = item.xpath('.//p[contains(@class, "css-u7ev33")]')
                location = location_elem[0].text_content().strip() if location_elem else "N/A"
                
                # Extract salary (optional)
                salary_elem = item.xpath('.//span[contains(@class, "chakra-badge")]')
                salary = ""
                for badge in salary_elem:
                    badge_text = badge.text_content().strip()
                    if "$" in badge_text or "year" in badge_text.lower() or "hour" in badge_text.lower():
                        salary = badge_text
                        break
                
                # Extract posted date
                date_elem = item.xpath('.//p[contains(@class, "css-13x1vyp")]')
                posted_date_str = date_elem[0].text_content().strip() if date_elem else ""
                posted_date = parse_posted_date(posted_date_str)
                
                # Create job URL
                job_url = f"{JOBS_URL}/?co=US&jk={job_key}"
                
                # Only include jobs from last 2 months
                if is_within_last_two_months(posted_date):
                    jobs.append({
                        "id": job_key,
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary": salary,
                        "posted_date": posted_date_str,
                        "url": job_url,
                        "posted_datetime": posted_date
                    })
                    logger.debug(f"Found job: {title} at {company} in {location}")
                
            except Exception as e:
                logger.debug(f"Error parsing job item: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(jobs)} job listings from HTML")
        return jobs
        
    except Exception as e:
        logger.error(f"Error parsing job listings HTML: {str(e)}")
        return []


async def fetch_job_details(job_key: str) -> Optional[str]:
    """
    Fetch full job description for a specific job using Selenium.
    Returns job description text.
    """
    try:
        url = f"{JOBS_URL}/?co=US&jk={job_key}"
        html_content = await fetch_page_with_selenium(url, wait_time=10)
        
        if not html_content:
            return None
        
        tree = html.fromstring(html_content)
        
        # Find job description in the right pane
        # Description is typically in a div with class containing the job details
        desc_elem = tree.xpath('//aside[contains(@aria-label, "")]//div[contains(@class, "css-14xyxow")]//div')
        if desc_elem:
            # Get all text content from description
            description = "\n".join([elem.text_content().strip() for elem in desc_elem if elem.text_content().strip()])
            return description
        
        # Fallback: try to find any div with job description
        desc_elem = tree.xpath('//div[contains(@class, "css-14xyxow")]//div//p')
        if desc_elem:
            description = "\n".join([p.text_content().strip() for p in desc_elem])
            return description
        
        return None
        
    except Exception as e:
        logger.debug(f"Error fetching job details for {job_key}: {str(e)}")
        return None


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
    Main function to fetch Stack Overflow Jobs data.
    Follows the same pattern as Hacker News module:
    1. Fetch job listings from Stack Overflow Jobs
    2. Parse HTML to extract job information
    3. Feed to AI extraction module
    4. Return structured data
    """
    start_time = time.perf_counter()
    logger.info("Starting Stack Overflow Jobs data fetch...")
    
    try:
        # Step 1: Fetch job listings using Selenium (first few pages)
        logger.info("Using Selenium to fetch JavaScript-rendered content...")
        all_jobs = []
        max_pages = 5  # Limit to first 5 pages (50 jobs per page = 250 jobs max)
        
        for page in range(1, max_pages + 1):
            html_content = await fetch_job_listings_page(page=page, country="US")
            
            if not html_content:
                logger.warning(f"Failed to fetch page {page}")
                break
            
            jobs = parse_job_listings(html_content)
            
            if not jobs:
                logger.info(f"No more jobs found on page {page}")
                break
            
            all_jobs.extend(jobs)
            logger.info(f"Fetched {len(jobs)} jobs from page {page} (total: {len(all_jobs)})")
            
            # Small delay between pages
            await asyncio.sleep(1)
            
            if not all_jobs:
                logger.warning("No job listings found")
                logger.warning("")
                logger.warning("⚠️  NOTE: Stack Overflow Jobs uses JavaScript-rendered content (Indeed white-label).")
                logger.warning("   If you're getting 403 errors, the site may be blocking automated requests.")
                logger.warning("   Consider:")
                logger.warning("   1. Using a headless browser (Selenium/Playwright)")
                logger.warning("   2. Using Indeed's official API if available")
                logger.warning("   3. Using alternative job sources (Hacker News, etc.)")
                return {}
            
            # Step 2: Extract job postings for AI extraction
            job_postings = extract_job_postings(all_jobs)
            
            if not job_postings["ids"]:
                logger.warning("No job postings extracted")
                return {}
            
            # Step 3: Feed to AI extraction module
            logger.info(f"Feeding {len(job_postings['ids'])} job postings to AI extraction...")
            try:
                from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
                extracted_data = await finalize_ai_extraction(job_postings)
            except Exception as e:
                logger.error(f"Failed to extract AI content from Stack Overflow Jobs data: {str(e)}")
                extracted_data = {}
            
            # Step 4: Format results
            llm_results = None
            if extracted_data:
                llm_results = copy.deepcopy(hiring_fetched_data)
                
                for key, value in extracted_data.items():
                    if key in llm_results and isinstance(llm_results[key], list):
                        llm_results[key].extend(value)
                    elif key in llm_results:
                        llm_results[key] = value
                
                # Set source and link
                llm_results["source"] = "StackOverflowJobs"
                llm_results["link"] = job_postings.get("urls", [])
            else:
                logger.warning("AI extraction for Stack Overflow Jobs returned no data")
            
            duration = time.perf_counter() - start_time
            
            # Print comprehensive summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("STACK OVERFLOW JOBS EXTRACTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏱️  Total time: {duration:.2f} seconds ({duration/60:.1f} minutes)")
            logger.info(f"📊 Input: {len(job_postings['ids'])} job postings processed")
            
            if llm_results:
                num_results = len(llm_results.get("article_id", []))
                logger.info(f"✅ Successfully extracted: {num_results} job postings")
                
                if num_results > 0:
                    # Get unique values (filter out empty strings)
                    companies = [c for c in llm_results.get('company_name', []) if c and str(c).strip()]
                    job_roles = []
                    for roles in llm_results.get('job_roles', []):
                        if isinstance(roles, list):
                            job_roles.extend([r for r in roles if r and str(r).strip()])
                        elif roles and str(roles).strip():
                            job_roles.append(roles)
                    
                    cities = [c for c in llm_results.get('city', []) if c and str(c).strip()]
                    countries = [c for c in llm_results.get('country', []) if c and str(c).strip()]
                    
                    logger.info("")
                    logger.info("📈 Extraction Statistics:")
                    logger.info(f"   • Unique Companies: {len(set(companies))}")
                    logger.info(f"   • Unique Job Roles: {len(set(job_roles))}")
                    logger.info(f"   • Unique Cities: {len(set(cities))}")
                    logger.info(f"   • Unique Countries: {len(set(countries))}")
                    
                    # Show top companies and roles
                    if companies:
                        from collections import Counter
                        top_companies = Counter(companies).most_common(5)
                        logger.info("")
                        logger.info("🏢 Top Companies:")
                        for company, count in top_companies:
                            logger.info(f"   • {company}: {count} posting(s)")
                    
                    if job_roles:
                        from collections import Counter
                        top_roles = Counter(job_roles).most_common(5)
                        logger.info("")
                        logger.info("💼 Top Job Roles:")
                        for role, count in top_roles:
                            logger.info(f"   • {role}: {count} posting(s)")
                    
                    # Show sample results
                    logger.info("")
                    logger.info("📋 Sample Results (first 3):")
                    for i in range(min(3, num_results)):
                        logger.info(f"   {i+1}. ID: {llm_results.get('article_id', [])[i]}")
                        logger.info(f"      Company: {llm_results.get('company_name', [])[i] if i < len(llm_results.get('company_name', [])) else 'N/A'}")
                        logger.info(f"      Role: {llm_results.get('job_roles', [])[i] if i < len(llm_results.get('job_roles', [])) else 'N/A'}")
                        logger.info(f"      Location: {llm_results.get('city', [])[i] if i < len(llm_results.get('city', [])) else 'N/A'}, {llm_results.get('country', [])[i] if i < len(llm_results.get('country', [])) else 'N/A'}")
                else:
                    logger.warning("⚠️  No items extracted from results")
            else:
                logger.warning("❌ No results extracted")
            
            logger.info("=" * 80)
            
            return llm_results if llm_results else {}
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


if __name__ == "__main__":
    asyncio.run(main())

