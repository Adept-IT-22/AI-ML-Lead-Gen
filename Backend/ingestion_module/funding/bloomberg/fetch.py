# This file fetches AI funding news from Bloomberg

import copy
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

# Sitemap URLs
SITEMAP_INDEX_URL = "https://www.bloomberg.com/sitemaps/news/index.xml"
SITEMAP_LATEST_URL = "https://www.bloomberg.com/sitemaps/news/latest.xml"

# Funding keywords
FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding', 'investment', 'funded']

# Configure semaphore for rate limiting
MAX_CONNECTIONS = 10

# XML namespaces
NAMESPACE = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9"
}

def is_within_last_two_months(date_str: Optional[str]) -> bool:
    """Check if a date string is within the last two months."""
    if not date_str:
        return False  # Exclude if no date available (fail closed)
    
    try:
        # Normalize: replace spaces with 'T' for ISO format, handle timezone colon
        # Input formats: "2025-11-05 12:01 +00:00" or "2025-11-05T12:01:00+00:00" or "2025-11-05T11:50:12Z"
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
        
        # Normalize date string to handle single-digit months/days (Bloomberg uses both formats)
        # e.g., "2025-9-30" -> "2025-09-30", "2025-11-6" -> "2025-11-06"
        if not 'T' in normalized_date and not '+' in normalized_date and not 'Z' in normalized_date:
            # Simple date format - normalize single-digit months/days
            parts = normalized_date.split('-')
            if len(parts) == 3:
                year, month, day = parts
                # Pad single-digit month with zero
                if len(month) == 1:
                    month = f'0{month}'
                # Pad single-digit day with zero
                if len(day) == 1:
                    day = f'0{day}'
                normalized_date = f'{year}-{month}-{day}'
        
        # Parse various date formats
        # Format: 2025-11-05 or 2025-11-05T11:50:12Z or 2025-11-05T12:01:00+0000
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # With timezone (normalized): 2025-11-05T12:01:00+0000
            "%Y-%m-%dT%H:%M%z",     # With timezone, no seconds: 2025-11-05T12:01+0000
            "%Y-%m-%dT%H:%M:%SZ",   # Z timezone
            "%Y-%m-%dT%H:%M:%S",    # Without timezone
            "%Y-%m-%dT%H:%M",       # Without timezone, no seconds
            "%Y-%m-%d",             # Date only: 2025-11-06
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
            
            # Normalize single-digit months/days if needed
            parts = date_part.split('-')
            if len(parts) == 3:
                year, month, day = parts
                # Pad single-digit month with zero
                if len(month) == 1:
                    month = f'0{month}'
                # Pad single-digit day with zero
                if len(day) == 1:
                    day = f'0{day}'
                date_part = f'{year}-{month}-{day}'
            
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

async def parse_sitemap_index(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse Bloomberg sitemap index and return relevant monthly sitemap URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap index: {url}")
    
    try:
        # Use cloudscraper to bypass anti-bot protection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=1
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
            logger.error(f"HTTP {response.status_code} error fetching sitemap index: {url}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            # Try to get response text for debugging
            try:
                logger.debug(f"Response text: {response.text[:500]}")
            except:
                pass
            return []
        
        # cloudscraper returns requests.Response
        # Check content encoding first
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        logger.debug(f"Content-Encoding header: {content_encoding}")
        
        # Try to get decompressed content
        # requests library should auto-decompress, but let's verify
        try:
            # First try response.text (should be auto-decompressed)
            if response.text and len(response.text) > 0:
                # Check if it starts with XML
                if response.text.strip().startswith('<?xml'):
                    content = response.text.encode('utf-8')
                    logger.debug(f"Successfully got XML from response.text ({len(content)} bytes)")
                else:
                    # Might still be compressed or error page
                    logger.warning(f"response.text doesn't look like XML. First 100 chars: {response.text[:100]}")
                    content = response.content
            else:
                content = response.content
        except Exception as e:
            logger.warning(f"Could not use response.text: {str(e)}")
            content = response.content
        
        # If content is still compressed (bytes), try manual decompression
        if isinstance(content, bytes) and not content.startswith(b'<?xml'):
            # Try gzip decompression
            if 'gzip' in content_encoding or content.startswith(b'\x1f\x8b'):
                import gzip
                try:
                    content = gzip.decompress(content)
                    logger.debug("Manually decompressed gzip content")
                except Exception as e:
                    logger.debug(f"Gzip decompression failed: {str(e)}")
            
            # Try brotli if available
            elif 'br' in content_encoding or content.startswith(b'\x81'):
                try:
                    import brotli
                    content = brotli.decompress(content)
                    logger.debug("Manually decompressed brotli content")
                except ImportError:
                    logger.warning("Brotli compression detected but brotli library not available")
                except Exception as e:
                    logger.debug(f"Brotli decompression failed: {str(e)}")
        
        logger.debug(f"Received {len(content)} bytes from sitemap index")
        
        # Check if content is empty
        if not content or len(content) == 0:
            logger.error(f"Empty response from sitemap index: {url}")
            return []
        
        # Try to decode as text to check if it's HTML error page or XML
        try:
            if isinstance(content, bytes):
                content_text = content.decode('utf-8')
            else:
                content_text = content
                
            if not content_text.strip().startswith('<?xml'):
                logger.error(f"Response is not XML. First 500 chars: {content_text[:500]}")
                return []
        except UnicodeDecodeError as e:
            logger.error(f"Could not decode response as UTF-8: {str(e)}")
            # Try to see what we got
            logger.debug(f"First 100 bytes (hex): {content[:100].hex() if isinstance(content, bytes) else str(content)[:100]}")
            return []
        
        # Try to parse XML
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {str(e)}")
            try:
                content_text = content.decode('utf-8')
                logger.debug(f"First 500 chars of response: {content_text[:500]}")
            except:
                logger.debug(f"First 500 bytes (hex): {content[:500].hex()}")
            return []
        
        sitemaps = []
        # Find all sitemap entries - try both with and without namespace
        sitemap_entries = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
        if not sitemap_entries:
            # Try without namespace
            sitemap_entries = root.findall('.//sitemap')
        
        logger.debug(f"Found {len(sitemap_entries)} sitemap entries in index")
        
        for sitemap_entry in sitemap_entries:
            # Try to find loc element with namespace
            loc_element = sitemap_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_element is None:
                # Try without namespace
                loc_element = sitemap_entry.find('.//loc')
            
            if loc_element is not None and loc_element.text:
                sitemap_url = loc_element.text.strip()
                
                # Get lastmod date
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
    """Parse Bloomberg monthly sitemap and extract URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap: {url}")
    
    try:
        # Use cloudscraper to bypass anti-bot protection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=1
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
            logger.error(f"HTTP {response.status_code} error fetching sitemap: {url}")
            return []
        
        # cloudscraper returns requests.Response, which has .content as bytes
        content = response.content
        logger.debug(f"Received {len(content)} bytes from sitemap")
        
        # Try to parse XML
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {str(e)}")
            logger.debug(f"First 500 chars of response: {content[:500]}")
            return []
        
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
                
                # Get publication date - prefer news:publication_date (more accurate) over lastmod
                publication_date = None
                
                # Try to get news:publication_date first (more accurate for article date)
                news_pub_date_element = url_entry.find('.//{http://www.google.com/schemas/sitemap-news/0.9}publication_date')
                if news_pub_date_element is not None and news_pub_date_element.text:
                    publication_date = news_pub_date_element.text.strip()
                else:
                    # Fallback to lastmod if news:publication_date is not available
                    lastmod_element = url_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    if lastmod_element is None:
                        lastmod_element = url_entry.find('.//lastmod')
                    if lastmod_element is not None and lastmod_element.text:
                        publication_date = lastmod_element.text.strip()
                
                articles.append({
                    'url': url_text,
                    'lastmod': publication_date  # Using publication_date for filtering
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
                   'neural network', 'llm', 'gpt', 'openai', 'chatgpt', 'generative ai']
    funding_keywords = ['funding', 'raises', 'closes', 'nets', 'secures', 'awarded', 
                       'notches', 'lands', 'investment', 'funded', 'investor', 'series',
                       'seed round', 'venture capital', 'vc', 'raised', 'million', 'billion']
    
    # Use word boundary matching to avoid false positives (e.g., "ai" in "raises")
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    return has_ai and has_funding

async def extract_and_filter_paragraphs(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs from a Bloomberg article URL and filter by AI funding keywords."""
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
            # Priority order: body-content div first (primary structure), then fallbacks
            paragraphs = []
            
            # Method 1: Extract from body-content div (primary structure for Bloomberg)
            # Structure: <div class="body-content"> with <p class="ArticleBodyText_articleBodyContent__..."> tags
            body_content_container = root.xpath("//div[contains(@class, 'body-content')]")
            if body_content_container:
                # Get all p tags within body-content
                all_p_tags = body_content_container[0].xpath(".//p[contains(@class, 'ArticleBodyText_articleBodyContent')]")
                
                paragraphs = []
                for p_tag in all_p_tags:
                    # Skip empty paragraphs and paywall content
                    text = p_tag.text_content().strip()
                    
                    # Get paragraph class to check for paywall
                    p_class = p_tag.get('class', '')
                    if isinstance(p_class, list):
                        p_class = ' '.join(p_class)
                    p_class_lower = p_class.lower()
                    
                    # Skip paywall paragraphs (Bloomberg marks paywall content with 'paywall' class)
                    if 'paywall' in p_class_lower:
                        continue
                    
                    # Filter out unwanted content
                    skip_texts = [
                        'Sign up', 'Enter your email', 'By submitting', 'Bloomberg may send',
                        'Privacy Policy', 'Terms of Service', 'Want more Bloomberg Opinion',
                        'More From Bloomberg Opinion', 'Subscribe', 'Newsletter',
                        'More From Bloomberg Opinion:', 'Want more Bloomberg Opinion?'
                    ]
                    
                    # Check if paragraph is inside unwanted containers (ads, newsletters, etc.)
                    parent = p_tag.getparent()
                    skip_paragraph = False
                    while parent is not None:
                        if parent.tag == 'div':
                            parent_class = parent.get('class', '')
                            if isinstance(parent_class, list):
                                parent_class = ' '.join(parent_class)
                            parent_class_lower = parent_class.lower()
                            # Skip paragraphs in newsletter, ad, or promotional sections
                            if any(unwanted in parent_class_lower for unwanted in ['newsletter', 'inline-newsletter', 'ad', 'ad-container', 'promotional', 'paywall-only', 'inline-newsletter-top', 'inline-newsletter-middle', 'inline-newsletter-bottom']):
                                skip_paragraph = True
                                break
                        parent = parent.getparent()
                    
                    # Filter out very short paragraphs and unwanted content
                    if (not skip_paragraph and text and len(text) > 50 and 
                        not any(skip in text for skip in skip_texts)):
                        paragraphs.append(text)
            
            # Method 2: Standard article content selectors (fallback)
            if not paragraphs:
                p_selectors = [
                    "//div[contains(@class, 'article-content')]//p",
                    "//article//p",
                    "//div[contains(@class, 'content')]//p",
                    "//main//p",
                    "//div[contains(@class, 'article')]//p"
                ]
                
                for selector in p_selectors:
                    paragraph_nodes = root.xpath(selector)
                    if paragraph_nodes:
                        paragraphs = [
                            node.text_content().strip() 
                            for node in paragraph_nodes 
                            if node.text_content().strip() and len(node.text_content().strip()) > 50
                        ]
                        if paragraphs:
                            break
            
            # Method 3: Fallback - extract from article or main content
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

async def fetch_bloomberg_data() -> Dict[str, List[str]]:
    """
    Main function to fetch Bloomberg data.

    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)

    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from Bloomberg...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Try to use latest.xml first (more efficient, contains only recent articles)
            logger.info(f"Attempting to use latest.xml sitemap: {SITEMAP_LATEST_URL}")
            latest_articles = await parse_sitemap(client, SITEMAP_LATEST_URL)
            
            if latest_articles:
                logger.info(f"Found {len(latest_articles)} articles in latest.xml")
                # Filter articles by date (last 2 months)
                recent_articles = [
                    article for article in latest_articles
                    if is_within_last_two_months(article.get('lastmod'))
                ]
                logger.info(f"Found {len(recent_articles)} articles from last 2 months in latest.xml")
            else:
                # Fallback to monthly sitemaps if latest.xml is not available
                logger.info("latest.xml not available or empty, falling back to monthly sitemaps")
                # Step 1: Parse sitemap index to get monthly sitemaps
                monthly_sitemaps = await parse_sitemap_index(client, SITEMAP_INDEX_URL)
                
                if not monthly_sitemaps:
                    logger.warning("No monthly sitemaps found in index")
                    return {"urls": [], "paragraphs": []}
                
                logger.info(f"Found {len(monthly_sitemaps)} monthly sitemaps in index")
                
                # Step 2: Filter monthly sitemaps by date (last 2 months)
                recent_sitemaps = [
                    sitemap for sitemap in monthly_sitemaps
                    if is_within_last_two_months(sitemap.get('lastmod'))
                ]
                
                logger.info(f"Found {len(recent_sitemaps)} monthly sitemaps from last 2 months")
                
                # Step 3: Parse each monthly sitemap to get article URLs
                all_articles = []
                for sitemap in recent_sitemaps:
                    articles = await parse_sitemap(client, sitemap['url'])
                    all_articles.extend(articles)
                
                if not all_articles:
                    logger.warning("No articles found in monthly sitemaps")
                    return {"urls": [], "paragraphs": []}
                
                logger.info(f"Found {len(all_articles)} total articles in monthly sitemaps")
                
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
            sample_failed_articles = []
            
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
                    elif len(sample_failed_articles) < 3:
                        # Log a few examples of articles that had content but didn't match
                        sample_failed_articles.append({
                            'url': url,
                            'title': title[:100] if title else 'No title',
                            'has_ai': any(re.search(r'\b' + re.escape(kw) + r'\b', f"{title} {content_text}".lower()) for kw in ['ai', 'artificial intelligence', 'machine learning', 'ml']),
                            'has_funding': any(kw in f"{title} {content_text}".lower() for kw in ['funding', 'raises', 'investment', 'funded', 'million', 'billion']),
                            'first_paragraph': paragraphs[0][:200] if paragraphs else 'No paragraphs'
                        })
            
            logger.info(f"Completed processing all {len(recent_articles)} articles")
            logger.info(f"Summary: {articles_with_content} articles had content, {articles_with_title} had titles, {articles_ai_funding} matched AI funding criteria")
            
            if sample_failed_articles:
                logger.info("Sample articles that didn't match AI funding criteria:")
                for i, article in enumerate(sample_failed_articles, 1):
                    logger.info(f"  {i}. {article['url']}")
                    logger.info(f"     Title: {article['title']}")
                    logger.info(f"     Has AI keywords: {article['has_ai']}, Has funding keywords: {article['has_funding']}")
                    logger.info(f"     First paragraph: {article['first_paragraph']}...")
            
            logger.info(f"Found {len(results['urls'])} AI funding articles from last 2 months")
            return results
            
    except Exception as e:
        logger.error(f"Error fetching Bloomberg data: {str(e)}")
        return {"urls": [], "paragraphs": []}

async def main():
    start_time = time.perf_counter()
    
    try:
        links_and_paragraphs = await fetch_bloomberg_data()
        
        if not links_and_paragraphs.get("urls") or not links_and_paragraphs.get("paragraphs"):
            logger.warning("AI extraction for Bloomberg returned no data. No logging will happen")
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
            logger.warning("AI extraction for Bloomberg returned no data. No logging will happen")
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
        llm_results["source"] = ["Bloomberg"] * num_companies
        llm_results["type"] = "funding"
        
        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Bloomberg took {elapsed_time:.2f} seconds")
        
        return llm_results
        
    except Exception as e:
        logger.error(f"Failed to extract AI content from Bloomberg data: {str(e)}")
        return copy.deepcopy(funding_data_dict)

