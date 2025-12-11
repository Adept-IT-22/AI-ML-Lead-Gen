"""
Crunchboard Jobs Parser
Fetches job listings from Crunchboard by parsing sitemap XML and scraping individual job pages.
Similar to other hiring modules, this parses structured data and feeds it to AI extraction.
"""

import time
import copy
import asyncio
import logging
import json
import re
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
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse date '{date_str}': {str(e)}")

    return None


def is_within_last_60_days(date_str: Optional[str]) -> bool:
    """Check if a job posting date is within the last 60 days."""
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
    semaphore: asyncio.Semaphore,
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


async def fetch_sitemap_index(semaphore: asyncio.Semaphore) -> List[str]:
    """Fetch the main sitemap index and return job sitemap URLs."""
    try:
        content = await fetch_with_scraper(SITEMAP_URL, semaphore=semaphore)
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


async def fetch_job_sitemap(sitemap_url: str, semaphore: asyncio.Semaphore) -> List[Dict[str, Optional[str]]]:
    """Fetch a job sitemap shard and return URL + lastmod entries."""
    try:
        content = await fetch_with_scraper(sitemap_url, semaphore=semaphore)
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


async def collect_recent_job_urls(semaphore: asyncio.Semaphore) -> List[str]:
    """Collect recent job URLs by walking the sitemap index."""
    sitemap_urls = await fetch_sitemap_index(semaphore)
    all_entries: List[Dict[str, Optional[str]]] = []

    if not sitemap_urls:
        logger.warning("No sitemap shards discovered; falling back to root sitemap parsing")
        all_entries.extend(await fetch_job_sitemap(SITEMAP_URL, semaphore))
    else:
        tasks = [fetch_job_sitemap(sitemap_url, semaphore) for sitemap_url in sitemap_urls]
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
        # Only include jobs with recent lastmod OR missing lastmod (with warning)
        if lastmod:
            if not is_within_last_60_days(lastmod):
                continue
        else:
            logger.debug(f"Job URL {url} has no lastmod date, including anyway")
        seen.add(url)
        recent_urls.append(url)

    logger.info(f"Collected {len(recent_urls)} recent Crunchboard job URLs")
    return recent_urls


class CrunchboardDescriptionParser(HTMLParser):
    """HTML parser to extract job description from Crunchboard pages."""
    
    def __init__(self):
        super().__init__()
        self.description = []
        self.in_job_body = False
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        
        # Look for the job-body div which contains the description
        if tag == 'div' and 'class' in attrs_dict:
            classes = attrs_dict['class'].split()
            if 'job-body' in classes:
                self.in_job_body = True
    
    def handle_endtag(self, tag):
        if tag == 'div' and self.in_job_body:
            self.in_job_body = False
        self.current_tag = None
    
    def handle_data(self, data):
        if self.in_job_body:
            text = data.strip()
            if text:
                self.description.append(text)
    
    def get_description(self) -> str:
        return ' '.join(self.description)


def extract_job_data(html_content: str, url: str) -> Optional[Dict[str, Any]]:
    """Extract job data from HTML page using JSON-LD and HTML parsing."""
    try:
        # First, try to extract from JSON-LD (most reliable)
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        json_match = re.search(json_ld_pattern, html_content, re.DOTALL)
        
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                
                # Extract data from JSON-LD
                title = json_data.get('title', '')
                company = ''
                if 'hiringOrganization' in json_data:
                    company = json_data['hiringOrganization'].get('name', '')
                
                description = json_data.get('description', '')
                # Clean HTML from description
                if description:
                    description = re.sub(r'<[^>]+>', ' ', description)
                    description = re.sub(r'\s+', ' ', description).strip()
                
                location = ''
                posted_date = json_data.get('datePosted', '')
                
                if title and description:
                    return {
                        "title": title,
                        "company": company,
                        "description": description,
                        "url": url,
                        "location": location,
                        "posted_at": posted_date
                    }
            except json.JSONDecodeError:
                pass
        
        # Fallback to HTML parsing
        parser = CrunchboardDescriptionParser()
        parser.feed(html_content)
        description = parser.get_description()
        
        # Extract title from h1
        title = ""
        h1_match = re.search(r'<h1[^>]*class="[^"]*u-textH2[^"]*"[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
        if h1_match:
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        
        # Extract company
        company = ""
        company_match = re.search(r'<div[^>]*class="[^"]*text-primary text-large[^"]*"[^>]*><strong>(.*?)</strong></div>', html_content, re.DOTALL)
        if company_match:
            company = re.sub(r'<[^>]+>', '', company_match.group(1)).strip()
        
        if not description:
            return None
        
        return {
            "title": title or "Job Listing",
            "company": company,
            "description": description,
            "url": url,
            "location": "",
            "posted_at": None
        }
    except Exception as e:
        logger.error(f"Failed to extract job data from {url}: {str(e)}")
        return None


async def fetch_job_page(url: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
    """Fetch a single job page and extract job data."""
    html_content = await fetch_with_scraper(url, semaphore=semaphore)
    if not html_content:
        return None
    return extract_job_data(html_content, url)


async def fetch_job_pages(urls: List[str], semaphore: asyncio.Semaphore) -> List[Dict[str, Any]]:
    """Fetch multiple job pages concurrently."""
    tasks = [fetch_job_page(url, semaphore) for url in urls]
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
        
        # Extract ID from URL, handling trailing slashes
        job_id = url.rstrip('/').split('/')[-1] or url
        job_postings["ids"].append(job_id)
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


async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch Crunchboard jobs and extract hiring information."""
    start_time = time.time()
    logger.info("Starting Crunchboard hiring ingestion...")
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    try:
        # Collect job URLs from sitemap shards
        job_urls = await collect_recent_job_urls(semaphore)
        
        if not job_urls:
            logger.warning("No recent job URLs found from Crunchboard sitemap")
            return None
        
        # Warm up session to obtain cookies before hitting individual job pages
        await fetch_with_scraper(f"{BASE_URL}/", semaphore=semaphore)

        # Fetch job pages
        logger.info(f"Fetching {len(job_urls)} job pages...")
        jobs = await fetch_job_pages(job_urls[:50], semaphore)  # Limit to 50 for testing
        
        if not jobs:
            logger.warning("No job postings extracted from Crunchboard")
            return None
        
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

        llm_results = None
        if extracted_data:
            llm_results = copy.deepcopy(hiring_fetched_data)
            for key, value in extracted_data.items():
                if key in llm_results and isinstance(llm_results[key], list) and isinstance(value, list):
                    llm_results[key].extend(value)
                else:
                    llm_results[key] = value

            llm_results["source"] = "crunchboard"
            llm_results["type"] = "hiring"
            # Validate that job_postings has expected keys
            if "urls" in job_postings:
                llm_results["link"] = job_postings["urls"]
            else:
                logger.warning("job_postings missing 'urls' key")
                llm_results["link"] = []
        else:
            logger.warning("AI extraction for Crunchboard returned no data")

        elapsed = time.time() - start_time
        # Validate job_postings has 'urls' before accessing
        job_count = len(job_postings.get('urls', []))
        logger.info(
            f"Crunchboard hiring ingestion completed in {elapsed:.2f} seconds with {job_count} extracted articles."
        )
        return llm_results
    
    except Exception as e:
        logger.error(f"Error in Crunchboard hiring ingestion: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    asyncio.run(main())

