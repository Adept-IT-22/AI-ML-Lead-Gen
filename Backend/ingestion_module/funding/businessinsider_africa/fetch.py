# This file fetches AI funding news from Business Insider Africa

import copy
import gzip
import time
import asyncio
import logging
import re
import httpx
import cloudscraper
from datetime import datetime, timedelta
from lxml import etree, html
from typing import Dict, List, Optional, Tuple
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

# Sitemap URLs - try multiple to find latest stories
SITEMAP_URLS = [
    "https://africa.businessinsider.com/sitemap-stories-latest.xml.gz",  # Most likely to have latest stories
    "https://africa.businessinsider.com/sitemap-articles-index.xml.gz",
    "https://africa.businessinsider.com/sitemap-categories.xml.gz",
    "https://africa.businessinsider.com/sitemap-topics.xml.gz"
]

FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding', 'investment', 'funded']

# Configure semaphore for rate limiting
MAX_CONNECTIONS = 10

# XML namespaces
NAMESPACE = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
}

async def fetch_gz_with_scraper(client: cloudscraper.CloudScraper, url: str) -> bytes:
    """Fetch .gz file using cloudscraper (handles anti-bot protection)."""
    response = await asyncio.to_thread(client.get, url)
    response.raise_for_status()
    return response.content

async def fetch_and_decompress_gz(client: cloudscraper.CloudScraper, url: str) -> Optional[bytes]:
    """Download and decompress a .gz file using cloudscraper."""
    logger.info(f"Downloading and decompressing: {url}")
    
    try:
        gz_content = await fetch_gz_with_scraper(client, url)
        decompressed = gzip.decompress(gz_content)
        logger.info(f"Successfully decompressed {len(decompressed)} bytes from {url}")
        return decompressed
    except Exception as e:
        logger.error(f"Error downloading/decompressing {url}: {str(e)}")
        return None

def is_within_last_two_months(date_str: Optional[str]) -> bool:
    """Check if a date string is within the last two months."""
    if not date_str:
        return False  # Exclude if no date available (fail closed)
    
    try:
        # Normalize: replace spaces with 'T' for ISO format, handle timezone colon
        # Input formats: "2025-11-05 12:01 +00:00" or "2025-11-05T12:01:00+00:00"
        normalized_date = date_str.replace(' ', 'T', 1)  # Replace first space with 'T'
        
        # Normalize timezone format: convert +00:00 to +0000 (remove colon)
        # Python's %z expects +0000 format, not +00:00
        if '+' in normalized_date:
            # Replace +HH:MM with +HHMM
            parts = normalized_date.rsplit('+', 1)
            if len(parts) == 2 and ':' in parts[1]:
                tz_part = parts[1]
                tz_normalized = tz_part.replace(':', '')
                normalized_date = parts[0] + '+' + tz_normalized
        elif normalized_date.count('-') > 2:
            # Handle negative timezone like -05:00
            if 'T' in normalized_date:
                date_part, time_part = normalized_date.split('T', 1)
                if '-' in time_part and time_part.count('-') > 0:
                    # Split time and timezone
                    time_and_tz = time_part.rsplit('-', 1)
                    if len(time_and_tz) == 2 and ':' in time_and_tz[1]:
                        tz_part = time_and_tz[1]
                        tz_normalized = tz_part.replace(':', '')
                        normalized_date = date_part + 'T' + time_and_tz[0] + '-' + tz_normalized
        
        # Parse various date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # With timezone (normalized): 2025-11-05T12:01:00+0000
            "%Y-%m-%dT%H:%M%z",     # With timezone, no seconds: 2025-11-05T12:01+0000
            "%Y-%m-%dT%H:%M:%SZ",   # Z timezone
            "%Y-%m-%dT%H:%M:%S",    # Without timezone
            "%Y-%m-%dT%H:%M",       # Without timezone, no seconds
            "%Y-%m-%d",             # Date only
        ]
        
        article_date = None
        for fmt in date_formats:
            try:
                if fmt.endswith('Z'):
                    # Handle Z timezone
                    date_str_clean = normalized_date.replace('Z', '+00:00')
                    if '+' in date_str_clean and ':' in date_str_clean.split('+')[1]:
                        parts = date_str_clean.rsplit('+', 1)
                        tz_normalized = parts[1].replace(':', '')
                        date_str_clean = parts[0] + '+' + tz_normalized
                    article_date = datetime.strptime(date_str_clean, fmt.replace('Z', '%z'))
                else:
                    article_date = datetime.strptime(normalized_date, fmt)
                break
            except ValueError:
                continue
        
        if not article_date:
            # Try to extract just the date part
            date_part = normalized_date.split('T')[0] if 'T' in normalized_date else normalized_date.split('+')[0].split('-')[:3]
            if isinstance(date_part, list):
                date_part = '-'.join(date_part)
            try:
                article_date = datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                return False  # Exclude if can't parse (fail closed)
        
        # Make both dates timezone-aware for comparison
        # If article_date is naive, assume UTC
        if article_date.tzinfo is None:
            from datetime import timezone
            article_date = article_date.replace(tzinfo=timezone.utc)
        
        # Compare with timezone-aware current time
        two_months_ago = datetime.now(article_date.tzinfo) - timedelta(days=60)
        return article_date >= two_months_ago
        
    except Exception as e:
        logger.debug(f"Error parsing date '{date_str}': {str(e)}")
        return False  # Exclude if can't parse (fail closed)

async def parse_sitemap(client: cloudscraper.CloudScraper, url: str) -> List[Dict[str, str]]:
    """Download, decompress, and parse a .gz sitemap, extracting URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap: {url}")
    
    try:
        # Download and decompress the .gz file
        decompressed_content = await fetch_and_decompress_gz(client, url)
        if not decompressed_content:
            return []
        
        # Parse the XML
        root = etree.fromstring(decompressed_content)
        
        articles = []
        # Find all URL entries - try both with and without namespace
        url_entries = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        if not url_entries:
            # Try without namespace
            url_entries = root.findall('.//url')
        
        logger.debug(f"Found {len(url_entries)} URL entries in sitemap")
        
        for url_entry in url_entries:
            # Try to find loc element with namespace
            loc_element = url_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_element is None:
                # Try without namespace
                loc_element = url_entry.find('.//loc')
            
            if loc_element is not None and loc_element.text:
                url_text = loc_element.text.strip()
                
                # Get lastmod date
                lastmod_element = url_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                if lastmod_element is None:
                    lastmod_element = url_entry.find('.//lastmod')
                lastmod = lastmod_element.text if lastmod_element is not None and lastmod_element.text else None
                
                articles.append({
                    'url': url_text,
                    'lastmod': lastmod
                })
        
        logger.info(f"Extracted {len(articles)} URLs from {url}")
        return articles
        
    except Exception as e:
        logger.error(f"Error parsing sitemap {url}: {str(e)}")
        return []

async def try_sitemaps(client: cloudscraper.CloudScraper, urls: List[str]) -> List[Dict[str, str]]:
    """Try multiple sitemap URLs and return articles from the first successful one."""
    all_articles = []
    
    for url in urls:
        logger.info(f"Trying sitemap: {url}")
        articles = await parse_sitemap(client, url)
        
        if articles:
            logger.info(f"Successfully parsed {url}, found {len(articles)} articles")
            all_articles.extend(articles)
            # Continue to try other sitemaps to get more articles
        else:
            logger.warning(f"No articles found in {url}, trying next sitemap...")
    
    return all_articles

def is_ai_funding_related_content(title: str, content: str) -> bool:
    """Check if article content is related to AI funding."""
    text = f"{title} {content}".lower()
    
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 
                   'neural network', 'llm', 'gpt', 'openai', 'chatgpt', 'generative ai']
    funding_keywords = ['funding', 'raises', 'closes', 'nets', 'secures', 'awarded', 
                       'notches', 'lands', 'investment', 'funded', 'investor', 'series',
                       'seed round', 'venture capital', 'vc', 'raised', 'million', 'billion']
    
    # Use word boundary matching to avoid false positives (e.g., "ai" in "raises")
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    return has_ai and has_funding

async def extract_and_filter_paragraphs(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs from a Business Insider Africa article URL and filter by AI funding keywords."""
    async with semaphore:
        try:
            # Use cloudscraper to bypass anti-bot protection for individual articles
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=0.5
            )
            # Add headers to mimic a real browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = await asyncio.to_thread(scraper.get, url, headers=headers, timeout=30)
            
            # Check status code
            if response.status_code != 200:
                logger.debug(f"HTTP {response.status_code} for article: {url}")
                return url, [], ""
            
            # Use response.text which handles encoding automatically
            try:
                html_content = response.text
                root = html.fromstring(html_content.encode('utf-8'))
            except Exception as e:
                logger.debug(f"Error parsing HTML from {url}: {str(e)}")
                return url, [], ""
            
            # Extract title
            title = ""
            title_selectors = [
                "//h1",
                "//title",
                "//meta[@property='og:title']/@content",
                "//meta[@name='twitter:title']/@content"
            ]
            
            for selector in title_selectors:
                title_nodes = root.xpath(selector)
                if title_nodes:
                    if isinstance(title_nodes[0], str):
                        title = title_nodes[0].strip()
                    else:
                        title = title_nodes[0].text_content().strip()
                    if title:
                        break
            
            # Extract paragraphs - try multiple selectors
            paragraphs = []
            
            # Method 1: Extract from article content divs
            content_selectors = [
                "//div[contains(@class, 'article-content')]//p",
                "//div[contains(@class, 'post-content')]//p",
                "//div[contains(@class, 'entry-content')]//p",
                "//article//p",
                "//div[contains(@class, 'content')]//p",
                "//main//p"
            ]
            
            for selector in content_selectors:
                paragraph_nodes = root.xpath(selector)
                if paragraph_nodes:
                    paragraphs = [
                        node.text_content().strip() 
                        for node in paragraph_nodes 
                        if node.text_content().strip() and len(node.text_content().strip()) > 50
                    ]
                    if paragraphs:
                        break
            
            # Method 2: Fallback - extract from article or main content
            if not paragraphs:
                article_nodes = root.xpath("//article | //main | //div[contains(@class, 'content')]")
                for node in article_nodes:
                    text_content = node.text_content()
                    if text_content and len(text_content) > 100:
                        # Split on double line breaks
                        parts = re.split(r'\n\s*\n+', text_content)
                        paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
                        if paragraphs:
                            break
            
            return url, paragraphs, title
            
        except Exception as e:
            logger.debug(f"Failed to fetch content from {url}: {str(e)}")
        
        return url, [], ""

async def fetch_businessinsider_africa_data() -> Dict[str, List[str]]:
    """
    Main function to fetch Business Insider Africa data.

    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)

    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from Business Insider Africa...")
    
    try:
        # Use cloudscraper for sitemap fetching
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=1
        )
        
        # Step 1: Try multiple sitemap URLs to find articles
        all_articles = await try_sitemaps(scraper, SITEMAP_URLS)
        
        if not all_articles:
            logger.warning("No articles found in any sitemap")
            return {"urls": [], "paragraphs": []}
        
        logger.info(f"Found {len(all_articles)} total articles across all sitemaps")
        
        # Step 2: Filter articles by date (last 2 months)
        recent_articles = [
            article for article in all_articles
            if is_within_last_two_months(article.get('lastmod'))
        ]
        
        logger.info(f"Found {len(recent_articles)} articles from last 2 months")
        
        # Step 3: Extract content and filter by AI funding keywords
        logger.info(f"Starting to fetch content from {len(recent_articles)} articles...")
        results = {"urls": [], "paragraphs": []}
        semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = [extract_and_filter_paragraphs(client, article['url'], semaphore) for article in recent_articles]
            
            completed = 0
            articles_with_content = 0
            articles_with_title = 0
            articles_ai_funding = 0
            
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs, title = await coroutine
                completed += 1
                if completed % 50 == 0:
                    logger.info(f"Processed {completed}/{len(recent_articles)} articles... (found {articles_ai_funding} AI funding articles so far)")
                
                if paragraphs:
                    articles_with_content += 1
                if title:
                    articles_with_title += 1
                
                if paragraphs and title:
                    # Check if content is AI funding related
                    content_text = '\n'.join(paragraphs)
                    if is_ai_funding_related_content(title, content_text):
                        articles_ai_funding += 1
                        results["urls"].append(url)
                        results["paragraphs"].append('\n\n'.join(paragraphs))
            
            logger.info(f"Completed processing all {len(recent_articles)} articles")
            logger.info(f"Summary: {articles_with_content} articles had content, {articles_with_title} had titles, {articles_ai_funding} matched AI funding criteria")
            logger.info(f"Found {len(results['urls'])} AI funding articles from last 2 months")
            return results
            
    except Exception as e:
        logger.error(f"Error fetching Business Insider Africa data: {str(e)}")
        return {"urls": [], "paragraphs": []}

async def main():
    start_time = time.perf_counter()
    
    try:
        links_and_paragraphs = await fetch_businessinsider_africa_data()
        
        if not links_and_paragraphs.get("urls") or not links_and_paragraphs.get("paragraphs"):
            logger.warning("AI extraction for Business Insider Africa returned no data. No logging will happen")
            return copy.deepcopy(funding_data_dict)
        
        # Log what's being passed to LLM for verification
        num_urls = len(links_and_paragraphs.get("urls", []))
        num_paragraphs = len(links_and_paragraphs.get("paragraphs", []))
        logger.info(f"Passing {num_urls} URLs and {num_paragraphs} paragraph contents to AI extraction")
        if num_paragraphs > 0:
            # Log first paragraph sample to verify content is being extracted
            first_paragraph = links_and_paragraphs.get("paragraphs", [])[0]
            logger.debug(f"First paragraph sample (first 200 chars): {first_paragraph[:200]}...")
        
        llm_results = await finalize_ai_extraction(links_and_paragraphs)
        
        if not llm_results:
            logger.warning("AI extraction for Business Insider Africa returned no data. No logging will happen")
            return copy.deepcopy(funding_data_dict)
        
        # Get number of companies extracted
        num_companies = len(llm_results.get("company_name", []))
        
        # Store source URLs - these correspond to the paragraphs that were processed
        # Each URL in links_and_paragraphs["urls"][i] is the source for paragraphs[i]
        source_urls = links_and_paragraphs.get("urls", [])
        llm_results["link"] = source_urls
        
        # Log source URL tracking for verification
        if source_urls:
            logger.info(f"Source URLs tracked: {len(source_urls)} URLs mapped to {num_companies} extracted companies")
            logger.debug(f"First few source URLs: {source_urls[:3]}")
        
        # Add source metadata
        llm_results["source"] = ["Business Insider Africa"] * num_companies
        llm_results["type"] = "funding"
        
        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Business Insider Africa took {elapsed_time:.2f} seconds")
        
        return llm_results
        
    except Exception as e:
        logger.error(f"Failed to extract AI content from Business Insider Africa data: {str(e)}")
        return copy.deepcopy(funding_data_dict)

