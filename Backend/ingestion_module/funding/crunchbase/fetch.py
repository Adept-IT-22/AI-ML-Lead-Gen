# This file fetches AI funding news from Crunchbase

import copy
import time
import asyncio
import logging
import re
import httpx
import cloudscraper
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    logging.warning("undetected_chromedriver not available. Crunchbase may not work properly.")
from datetime import datetime, timedelta
from lxml import etree, html
from typing import Dict, List, Optional, Tuple
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

# Sitemap URL
SITEMAP_INDEX_URL = "https://www.crunchbase.com/www-sitemaps/sitemap-index.xml"

# Funding keywords
FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding', 'investment', 'funded']

# Configure semaphore for rate limiting
MAX_CONNECTIONS = 10

# XML namespaces
NAMESPACE = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
}

def is_within_last_two_months(date_str: Optional[str]) -> bool:
    """Check if a date string is within the last two months."""
    if not date_str:
        return False  # Exclude if no date available (fail closed)
    
    try:
        # Normalize: replace spaces with 'T' for ISO format, handle timezone colon
        normalized_date = date_str.replace(' ', 'T', 1)  # Replace first space with 'T'
        
        # Normalize timezone format: convert +00:00 to +0000 (remove colon)
        if '+' in normalized_date:
            parts = normalized_date.rsplit('+', 1)
            if len(parts) == 2 and ':' in parts[1]:
                tz_part = parts[1]
                tz_normalized = tz_part.replace(':', '')
                normalized_date = parts[0] + '+' + tz_normalized
        elif normalized_date.count('-') > 2:
            if 'T' in normalized_date:
                date_part, time_part = normalized_date.split('T', 1)
                if '-' in time_part and time_part.count('-') > 0:
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
            date_part = normalized_date.split('T')[0] if 'T' in normalized_date else normalized_date.split('+')[0].split('-')[:3]
            if isinstance(date_part, list):
                date_part = '-'.join(date_part)
            try:
                article_date = datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                return False  # Exclude if can't parse (fail closed)
        
        # Make both dates timezone-aware for comparison
        if article_date.tzinfo is None:
            from datetime import timezone
            article_date = article_date.replace(tzinfo=timezone.utc)
        
        # Compare with timezone-aware current time
        two_months_ago = datetime.now(article_date.tzinfo) - timedelta(days=60)
        return article_date >= two_months_ago
        
    except Exception as e:
        logger.debug(f"Error parsing date '{date_str}': {str(e)}")
        return False  # Exclude if can't parse (fail closed)

async def parse_sitemap_index(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse Crunchbase sitemap index and return child sitemap URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap index: {url}")
    
    try:
        # Crunchbase uses strong Cloudflare protection that requires JavaScript execution
        # Use undetected_chromedriver if available, otherwise fall back to cloudscraper
        if UC_AVAILABLE:
            logger.debug("Using undetected_chromedriver to bypass Cloudflare protection...")
            def fetch_with_uc():
                options = uc.ChromeOptions()
                # Try non-headless first - Cloudflare often blocks headless browsers
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--window-size=1920,1080')
                
                driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
                try:
                    # Visit homepage first to establish session
                    logger.debug("Visiting Crunchbase homepage to establish session...")
                    driver.get('https://www.crunchbase.com/')
                    
                    # Wait for Cloudflare challenge to complete
                    max_wait = 30
                    wait_interval = 2
                    waited = 0
                    while waited < max_wait:
                        page_source = driver.page_source.lower()
                        if 'cloudflare' not in page_source and 'challenge' not in page_source and '<iframe' not in page_source:
                            if 'crunchbase' in page_source or len(page_source) > 10000:
                                logger.debug("Successfully passed Cloudflare challenge on homepage")
                                break
                        time.sleep(wait_interval)
                        waited += wait_interval
                        if waited % 5 == 0:
                            logger.debug(f"Still waiting for Cloudflare challenge... ({waited}s)")
                    
                    if waited >= max_wait:
                        logger.warning("Timeout waiting for Cloudflare challenge on homepage")
                    
                    # Now fetch the sitemap index
                    logger.debug("Fetching sitemap index...")
                    driver.get(url)
                    
                    # Wait for XML content to appear
                    max_wait = 30
                    waited = 0
                    while waited < max_wait:
                        page_source = driver.page_source
                        if '<sitemapindex' in page_source or '<?xml' in page_source or '<sitemap' in page_source:
                            logger.debug("Found XML content in sitemap index")
                            break
                        page_lower = page_source.lower()
                        if 'cloudflare' in page_lower or 'challenge' in page_lower or '<iframe' in page_lower:
                            logger.debug(f"Still behind Cloudflare on sitemap index... ({waited}s)")
                        time.sleep(wait_interval)
                        waited += wait_interval
                    
                    if waited >= max_wait:
                        logger.warning("Timeout waiting for sitemap index XML content")
                    
                    content = driver.page_source.encode('utf-8')
                    logger.debug(f"Retrieved {len(content)} bytes from sitemap index")
                    return content
                except Exception as e:
                    logger.error(f"Error fetching with undetected_chromedriver: {str(e)}")
                    raise
                finally:
                    try:
                        driver.quit()
                    except:
                        pass
            
            content = await asyncio.to_thread(fetch_with_uc)
        else:
            # Fallback to cloudscraper (may not work for Crunchbase)
            logger.warning("undetected_chromedriver not available, using cloudscraper (may fail)...")
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=3
            )
            response = await asyncio.to_thread(scraper.get, url, timeout=90)
            if response.status_code != 200:
                logger.error(f"Cloudscraper failed with status {response.status_code}")
                return []
            content = response.content
        
        logger.debug(f"Received {len(content)} bytes from sitemap index")
        
        # Check if response is HTML (Access Denied page) instead of XML
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html') or b'Access Denied' in content or b'AccessDenied' in content or b'<iframe' in content or b'blocked' in content.lower():
            logger.error(f"Crunchbase returned Access Denied/Challenge page instead of XML sitemap")
            logger.debug(f"Response content (first 500 chars): {content[:500].decode('utf-8', errors='ignore')}")
            return []
        
        # Extract XML from HTML if embedded
        if b'<sitemapindex' in content:
            xml_start = content.find(b'<sitemapindex')
            if xml_start > 0:
                xml_end = content.find(b'</sitemapindex>') + len(b'</sitemapindex>')
                if xml_end > xml_start:
                    content = content[xml_start:xml_end]
        
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {str(e)}")
            logger.debug(f"First 500 chars of response: {content[:500].decode('utf-8', errors='ignore')}")
            return []
        
        sitemaps = []
        # Find all sitemap entries - try both with and without namespace
        sitemap_entries = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
        if not sitemap_entries:
            sitemap_entries = root.findall('.//sitemap')
        
        logger.debug(f"Found {len(sitemap_entries)} sitemap entries in index")
        
        for sitemap_entry in sitemap_entries:
            loc_element = sitemap_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_element is None:
                loc_element = sitemap_entry.find('.//loc')
            
            if loc_element is not None and loc_element.text:
                sitemap_url = loc_element.text.strip()
                
                lastmod_element = sitemap_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                if lastmod_element is None:
                    lastmod_element = sitemap_entry.find('.//lastmod')
                lastmod = lastmod_element.text if lastmod_element is not None and lastmod_element.text else None
                
                sitemaps.append({
                    'url': sitemap_url,
                    'lastmod': lastmod
                })
        
        logger.info(f"Extracted {len(sitemaps)} sitemaps from index")
        return sitemaps
        
    except Exception as e:
        logger.error(f"Error parsing sitemap index {url}: {str(e)}")
        return []

async def parse_sitemap(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse Crunchbase sitemap and extract URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap: {url}")
    
    try:
        # Use cloudscraper for individual sitemaps (may need undetected_chromedriver if blocked)
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=1
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = await asyncio.to_thread(scraper.get, url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} error fetching sitemap: {url}")
            return []
        
        content = response.content
        root = etree.fromstring(content)
        
        articles = []
        # Find all URL entries - try both with and without namespace
        url_entries = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        if not url_entries:
            url_entries = root.findall('.//url')
        
        logger.debug(f"Found {len(url_entries)} URL entries in sitemap")
        
        for url_entry in url_entries:
            loc_element = url_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_element is None:
                loc_element = url_entry.find('.//loc')
            
            if loc_element is not None and loc_element.text:
                url_text = loc_element.text.strip()
                
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

def is_ai_funding_related_content(title: str, content: str) -> bool:
    """Check if article content is related to AI funding."""
    text = f"{title} {content}".lower()
    
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 
                   'neural network', 'llm', 'large language model', 'genai', 'generative ai']
    
    funding_keywords = FUNDING_KEYWORDS + ['raised', 'raise', 'invest', 'investor', 'venture', 
                                           'capital', 'series', 'round', 'seed', 'funding']
    
    # Use word boundary matching to avoid false positives
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    return has_ai and has_funding

async def extract_and_filter_paragraphs(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs from a Crunchbase article URL and filter by AI funding keywords."""
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
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = await asyncio.to_thread(scraper.get, url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.debug(f"HTTP {response.status_code} for article: {url}")
                return url, [], ""
            
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
            
            # Extract paragraphs - try multiple selectors for Crunchbase structure
            paragraphs = []
            
            content_selectors = [
                "//div[contains(@class, 'article-content')]//p",
                "//div[contains(@class, 'content')]//p",
                "//article//p",
                "//div[contains(@class, 'post-content')]//p",
                "//main//p",
                "//div[contains(@class, 'body')]//p"
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
            
            # Fallback - extract from article or main content
            if not paragraphs:
                article_nodes = root.xpath("//article | //main | //div[contains(@class, 'content')]")
                for node in article_nodes:
                    text_content = node.text_content()
                    if text_content and len(text_content) > 100:
                        parts = re.split(r'\n\s*\n+', text_content)
                        paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
                        if paragraphs:
                            break
            
            return url, paragraphs, title
            
        except Exception as e:
            logger.debug(f"Failed to fetch content from {url}: {str(e)}")
        
        return url, [], ""

async def fetch_crunchbase_data() -> Dict[str, List[str]]:
    """
    Main function to fetch Crunchbase data.

    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)

    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from Crunchbase...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Parse sitemap index to get child sitemaps
            sitemap_entries = await parse_sitemap_index(client, SITEMAP_INDEX_URL)
            
            if not sitemap_entries:
                logger.warning("No sitemaps found in index")
                return {"urls": [], "paragraphs": []}
            
            logger.info(f"Found {len(sitemap_entries)} sitemaps in index")
            
            # Step 2: Filter sitemaps by date (last 2 months)
            recent_sitemaps = [
                sitemap for sitemap in sitemap_entries
                if is_within_last_two_months(sitemap.get('lastmod'))
            ]
            
            logger.info(f"Found {len(recent_sitemaps)} recent sitemaps from index (last 2 months)")
            
            if not recent_sitemaps:
                logger.warning("No recent sitemaps found (last 2 months)")
                return {"urls": [], "paragraphs": []}
            
            # Step 3: Parse recent sitemaps to get articles
            all_articles = []
            tasks = [parse_sitemap(client, entry['url']) for entry in recent_sitemaps]
            
            for coroutine in asyncio.as_completed(tasks):
                articles = await coroutine
                all_articles.extend(articles)
            
            if not all_articles:
                logger.warning("No articles found in recent sitemaps")
                return {"urls": [], "paragraphs": []}
            
            logger.info(f"Found {len(all_articles)} total articles across all sitemaps")
            
            # Step 4: Filter articles by date (last 2 months)
            recent_articles = [
                article for article in all_articles
                if is_within_last_two_months(article.get('lastmod'))
            ]
            
            logger.info(f"Found {len(recent_articles)} articles from last 2 months")
            
            # Step 5: Extract content and filter by AI funding keywords
            logger.info(f"Starting to fetch content from {len(recent_articles)} articles...")
            results = {"urls": [], "paragraphs": []}
            semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
            
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
        logger.error(f"Error fetching Crunchbase data: {str(e)}")
        return {"urls": [], "paragraphs": []}

async def main():
    start_time = time.perf_counter()
    
    try:
        links_and_paragraphs = await fetch_crunchbase_data()
        
        if not links_and_paragraphs.get("urls") or not links_and_paragraphs.get("paragraphs"):
            logger.warning("AI extraction for Crunchbase returned no data. No logging will happen")
            return copy.deepcopy(funding_data_dict)
        
        # Log what's being passed to LLM for verification
        num_urls = len(links_and_paragraphs.get("urls", []))
        num_paragraphs = len(links_and_paragraphs.get("paragraphs", []))
        logger.info(f"Passing {num_urls} URLs and {num_paragraphs} paragraph contents to AI extraction")
        if num_paragraphs > 0:
            first_paragraph = links_and_paragraphs.get("paragraphs", [])[0]
            logger.debug(f"First paragraph sample (first 200 chars): {first_paragraph[:200]}...")
        
        llm_results = await finalize_ai_extraction(links_and_paragraphs)
        
        if not llm_results:
            logger.warning("AI extraction for Crunchbase returned no data. No logging will happen")
            return copy.deepcopy(funding_data_dict)
        
        # Get number of companies extracted
        num_companies = len(llm_results.get("company_name", []))
        
        # Store source URLs
        source_urls = links_and_paragraphs.get("urls", [])
        llm_results["link"] = source_urls
        
        # Log source URL tracking for verification
        if source_urls:
            logger.info(f"Source URLs tracked: {len(source_urls)} URLs mapped to {num_companies} extracted companies")
            logger.debug(f"First few source URLs: {source_urls[:3]}")
        
        # Add source metadata
        llm_results["source"] = ["Crunchbase"] * num_companies
        llm_results["type"] = "funding"
        
        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Crunchbase took {elapsed_time:.2f} seconds")
        
        return llm_results
        
    except Exception as e:
        logger.error(f"Failed to extract AI content from Crunchbase data: {str(e)}")
        return copy.deepcopy(funding_data_dict)

