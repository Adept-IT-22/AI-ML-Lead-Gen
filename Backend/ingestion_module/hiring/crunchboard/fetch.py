"""
Crunchboard Jobs Parser
Fetches job listings from Crunchboard by parsing sitemap XML and scraping individual job pages.
Similar to other hiring modules, this parses structured data and feeds it to AI extraction.
"""

import time
import copy
import asyncio
import logging
import requests
import cloudscraper
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from xml.etree import ElementTree as ET
from html.parser import HTMLParser
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data as hiring_fetched_data

logger = logging.getLogger(__name__)

# Base URL
BASE_URL = "https://www.crunchboard.com"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

# Rate limiting
MAX_CONCURRENT = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date from various formats."""
    if not date_str:
        return None
    
    try:
        # Try ISO format
        if 'T' in date_str:
            dt_value = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('.')[0])
        # Try simple date format
        elif len(date_str) == 10 and date_str.count('-') == 2:
            dt_value = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt_value = None

        if dt_value and dt_value.tzinfo is not None and dt_value.tzinfo.utcoffset(dt_value) is not None:
            return dt_value.astimezone(timezone.utc).replace(tzinfo=None)

        return dt_value
    except Exception as e:
        logger.debug(f"Failed to parse date '{date_str}': {str(e)}")

    return None


def is_within_last_two_months(date_str: Optional[str]) -> bool:
    """Check if a job posting date is within the last 2 months."""
    if not date_str:
        return False
    
    parsed_date = parse_date(date_str)
    if not parsed_date:
        return False
    
    two_months_ago = datetime.now() - timedelta(days=60)
    return parsed_date >= two_months_ago


CRUNCHBOARD_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Referer": f"{BASE_URL}/",
    "Origin": BASE_URL,
}

scraper = cloudscraper.create_scraper(
    delay=10,
    browser={"browser": "chrome", "platform": "windows", "mobile": False},
)
scraper.headers.update(CRUNCHBOARD_HEADERS)


async def fetch_with_scraper(
    url: str,
    *,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Optional[str]:
    """Fetch a URL using the shared Cloudscraper session with concurrency control."""
    async with semaphore:
        try:
            def _request() -> str:
                response = scraper.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers or CRUNCHBOARD_HEADERS,
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.text

            return await asyncio.to_thread(_request)
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", "unknown")
            logger.error(f"Failed to fetch {url}: HTTP {status} - {http_err}")
            return None
        except Exception as exc:
            logger.error(f"Failed to fetch {url}: {str(exc)}")
            return None


async def fetch_sitemap_index() -> List[str]:
    """Fetch the main sitemap index and return job sitemap URLs."""
    try:
        content = await fetch_with_scraper(SITEMAP_URL)
        if not content:
            return []

        root = ET.fromstring(content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        sitemap_urls: List[str] = []

        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('ns:sitemap', namespaces):
                loc = sitemap.find('ns:loc', namespaces)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if '/sitemaps/jobs/' in url or 'job_sitemap' in url:
                        sitemap_urls.append(url)
        elif root.tag.endswith('urlset'):
            # Fallback: root already contains job URLs
            sitemap_urls.append(SITEMAP_URL)

        logger.info(f"Found {len(sitemap_urls)} job sitemap shards from index")
        return sitemap_urls
    except Exception as e:
        logger.error(f"Failed to fetch/parse sitemap index: {str(e)}")
        return []


async def fetch_job_sitemap(sitemap_url: str) -> List[Dict[str, Optional[str]]]:
    """Fetch a job sitemap shard and return URL + lastmod entries."""
    try:
        content = await fetch_with_scraper(sitemap_url)
        if not content:
            return []

        root = ET.fromstring(content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        entries: List[Dict[str, Optional[str]]] = []
        for url_elem in root.findall('ns:url', namespaces):
            loc = url_elem.find('ns:loc', namespaces)
            lastmod = url_elem.find('ns:lastmod', namespaces)
            if loc is None or not loc.text:
                continue

            url = loc.text.strip()
            if '/jobs/' not in url and '/job/' not in url:
                continue

            entries.append({
                "url": url,
                "lastmod": lastmod.text.strip() if lastmod is not None and lastmod.text else None
            })

        logger.info(f"Fetched {len(entries)} job entries from sitemap shard {sitemap_url}")
        return entries
    except Exception as e:
        logger.error(f"Failed to fetch/parse job sitemap {sitemap_url}: {str(e)}")
        return []


async def collect_recent_job_urls() -> List[str]:
    """Collect recent job URLs by walking the sitemap index."""
    sitemap_urls = await fetch_sitemap_index()
    all_entries: List[Dict[str, Optional[str]]] = []

    if not sitemap_urls:
        logger.warning("No sitemap shards discovered; falling back to root sitemap parsing")
        all_entries.extend(await fetch_job_sitemap(SITEMAP_URL))
    else:
        tasks = [fetch_job_sitemap(sitemap_url) for sitemap_url in sitemap_urls]
        results = await asyncio.gather(*tasks)
        for entries in results:
            all_entries.extend(entries)

    if not all_entries:
        return []

    recent_urls: List[str] = []
    seen: Set[str] = set()
    for entry in all_entries:
        url = entry.get("url")
        lastmod = entry.get("lastmod")
        if not url or url in seen:
            continue
        if lastmod and not is_within_last_two_months(lastmod):
            continue
        seen.add(url)
        recent_urls.append(url)

    logger.info(f"Collected {len(recent_urls)} recent Crunchboard job URLs")
    return recent_urls


class CrunchboardDescriptionParser(HTMLParser):
    """HTML parser to extract job description from Crunchboard pages."""
    
    def __init__(self):
        super().__init__()
        self.description = []
        self.in_description = False
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        
        # Look for description containers
        if tag == 'div' and ('class' in attrs_dict and 'description' in attrs_dict['class']):
            self.in_description = True
        elif tag == 'div' and ('itemprop' in attrs_dict and attrs_dict['itemprop'] == 'description'):
            self.in_description = True
    
    def handle_endtag(self, tag):
        if tag == 'div' and self.in_description:
            self.in_description = False
        self.current_tag = None
    
    def handle_data(self, data):
        if self.in_description:
            text = data.strip()
            if text:
                self.description.append(text)
    
    def get_description(self) -> str:
        return ' '.join(self.description)


def extract_job_data(html_content: str, url: str) -> Optional[Dict[str, Any]]:
    """Extract job data from HTML page."""
    try:
        parser = CrunchboardDescriptionParser()
        parser.feed(html_content)
        description = parser.get_description()
        
        # Try to extract title, company, etc. from HTML
        # This is a simplified version - you may need to enhance based on actual page structure
        title = ""
        company = ""
        
        # Basic extraction (can be enhanced with BeautifulSoup if needed)
        if '<h1' in html_content:
            # Try to find title in h1 tag
            import re
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
            if h1_match:
                title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        
        if not description:
            return None
        
        return {
            "title": title or "Job Listing",
            "company": company,
            "description": description,
            "url": url
        }
    except Exception as e:
        logger.error(f"Failed to extract job data from {url}: {str(e)}")
        return None


async def fetch_job_page(url: str) -> Optional[Dict[str, Any]]:
    """Fetch a single job page and extract job data."""
    html_content = await fetch_with_scraper(url)
    if not html_content:
        return None
    return extract_job_data(html_content, url)


async def fetch_job_pages(urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch multiple job pages concurrently."""
    tasks = [fetch_job_page(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return [job for job in results if job]


def build_job_postings(jobs: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Build job postings structure for AI extraction."""
    job_postings: Dict[str, List[Any]] = {
        "ids": [],
        "urls": [],
        "titles": [],
        "metadata": []
    }
    
    seen_urls = set()
    
    for job in jobs:
        url = job.get("url", "")
        if not url or url in seen_urls:
            continue
        
        seen_urls.add(url)
        
        title = job.get("title", "Job Listing")
        company = job.get("company", "")
        description = job.get("description", "")
        
        # Build formatted title with description snippet
        formatted_title = title
        if company:
            formatted_title += f" at {company}"
        if description:
            desc_snippet = description[:200] + "..." if len(description) > 200 else description
            formatted_title += f" | {desc_snippet}"
        
        job_postings["ids"].append(url.split('/')[-1] or url)
        job_postings["urls"].append(url)
        job_postings["titles"].append(formatted_title)
        
        # Add metadata for richer extraction
        job_postings["metadata"].append({
            "job_title": title,
            "company": company,
            "location": job.get("location", ""),
            "description": description,
            "posted_at": job.get("posted_at"),
            "raw_source": "crunchboard"
        })
    
    return job_postings


async def main():
    """Main function to fetch Crunchboard jobs and extract hiring information."""
    start_time = time.time()
    logger.info("Starting Crunchboard hiring ingestion...")
    
    try:
        # Collect job URLs from sitemap shards
        job_urls = await collect_recent_job_urls()
        
        if not job_urls:
            logger.warning("No recent job URLs found from Crunchboard sitemap")
            return
        
        # Warm up session to obtain cookies before hitting individual job pages
        await fetch_with_scraper(f"{BASE_URL}/")

        # Fetch job pages
        logger.info(f"Fetching {len(job_urls)} job pages...")
        jobs = await fetch_job_pages(job_urls[:50])  # Limit to 50 for testing
        
        if not jobs:
            logger.warning("No job postings extracted from Crunchboard")
            return {}
        
        # Build job postings structure
        job_postings = build_job_postings(jobs)
        
        logger.info(f"Extracted {len(job_postings['urls'])} job postings from Crunchboard")
        
        # Feed to AI extraction
        extracted_data: Dict[str, List[Any]] = {}
        if job_postings["urls"]:
            try:
                extracted_data = await finalize_ai_extraction(job_postings)
            except Exception as extraction_error:
                logger.error(f"Failed to extract AI content from Crunchboard data: {extraction_error}")

        llm_results = {}
        if extracted_data:
            llm_results = copy.deepcopy(hiring_fetched_data)
            for key, value in extracted_data.items():
                if key in llm_results and isinstance(llm_results[key], list) and isinstance(value, list):
                    llm_results[key].extend(value)
                else:
                    llm_results[key] = value

            llm_results["source"] = "crunchboard"
            llm_results["type"] = "hiring"
            llm_results["link"] = job_postings.get("urls", [])
        else:
            logger.warning("AI extraction for Crunchboard returned no data")

        elapsed = time.time() - start_time
        logger.info(
            f"Crunchboard hiring ingestion completed in {elapsed:.2f} seconds with {len(job_postings['urls'])} extracted articles."
        )
        return llm_results if llm_results else {}
    
    except Exception as e:
        logger.error(f"Error in Crunchboard hiring ingestion: {str(e)}", exc_info=True)
        return {}


if __name__ == "__main__":
    asyncio.run(main())

