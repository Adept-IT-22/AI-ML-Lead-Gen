# This file fetches AI funding news from Forbes

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
    logging.warning("undetected_chromedriver not available. Forbes may not work properly.")
from datetime import datetime, timedelta
from lxml import etree, html
from typing import Dict, List, Optional, Tuple
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

# Sitemap URL
SITEMAP_URL = "https://www.forbes.com/news_sitemap.xml"

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
        
        # Parse various date formats
        # Format: 2025-11-05T11:50:12Z or 2025-11-05T12:01:00+0000
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # With timezone (normalized): 2025-11-05T12:01:00+0000
            "%Y-%m-%dT%H:%M%z",     # With timezone, no seconds: 2025-11-05T12:01+0000
            "%Y-%m-%dT%H:%M:%SZ",   # Z timezone
            "%Y-%m-%dT%H:%M:%S",    # Without timezone
            "%Y-%m-%dT%H:%M",      # Without timezone, no seconds
            "%Y-%m-%d",             # Date only
        ]
        
        article_date = None
        for fmt in date_formats:
            try:
                if fmt.endswith('Z'):
                    # Handle Z timezone
                    date_str_clean = normalized_date.replace('Z', '+00:00')
                    if ':' in date_str_clean.split('+')[1]:
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

async def parse_sitemap(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse Forbes news sitemap and extract URLs with their publication dates."""
    logger.info(f"Parsing sitemap: {url}")
    
    try:
        # Forbes uses strong Cloudflare protection that requires JavaScript execution
        # Use undetected_chromedriver if available, otherwise fall back to cloudscraper
        if UC_AVAILABLE:
            logger.debug("Using undetected_chromedriver to bypass Cloudflare protection...")
            # Use undetected_chromedriver in a thread to avoid blocking
            def fetch_with_uc():
                options = uc.ChromeOptions()
                # Try non-headless first - Cloudflare often blocks headless browsers
                # options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--window-size=1920,1080')
                # Remove incompatible experimental options
                # options.add_experimental_option("excludeSwitches", ["enable-automation"])
                # options.add_experimental_option('useAutomationExtension', False)
                
                driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
                try:
                    # Visit homepage first to establish session
                    logger.debug("Visiting Forbes homepage to establish session...")
                    driver.get('https://www.forbes.com/')
                    
                    # Wait for Cloudflare challenge to complete - check for actual content
                    max_wait = 30  # Maximum wait time in seconds
                    wait_interval = 2
                    waited = 0
                    while waited < max_wait:
                        page_source = driver.page_source.lower()
                        # Check if we got past Cloudflare (look for Forbes content, not challenge)
                        if 'cloudflare' not in page_source and 'challenge' not in page_source and '<iframe' not in page_source:
                            if 'forbes' in page_source or len(page_source) > 10000:  # Real content
                                logger.debug("Successfully passed Cloudflare challenge on homepage")
                                break
                        time.sleep(wait_interval)
                        waited += wait_interval
                        if waited % 5 == 0:
                            logger.debug(f"Still waiting for Cloudflare challenge... ({waited}s)")
                    
                    if waited >= max_wait:
                        logger.warning("Timeout waiting for Cloudflare challenge on homepage")
                    
                    # Now fetch the sitemap
                    logger.debug("Fetching sitemap...")
                    driver.get(url)
                    
                    # Wait for XML content to appear (not just any page)
                    max_wait = 30
                    waited = 0
                    while waited < max_wait:
                        page_source = driver.page_source
                        # Check if we have actual XML content
                        if '<urlset' in page_source or '<?xml' in page_source:
                            logger.debug("Found XML content in sitemap")
                            break
                        # Check if still behind Cloudflare
                        page_lower = page_source.lower()
                        if 'cloudflare' in page_lower or 'challenge' in page_lower or '<iframe' in page_lower:
                            logger.debug(f"Still behind Cloudflare on sitemap... ({waited}s)")
                        time.sleep(wait_interval)
                        waited += wait_interval
                    
                    if waited >= max_wait:
                        logger.warning("Timeout waiting for sitemap XML content")
                    
                    # Get page source
                    content = driver.page_source.encode('utf-8')
                    logger.debug(f"Retrieved {len(content)} bytes from sitemap")
                    return content
                except Exception as e:
                    logger.error(f"Error fetching with undetected_chromedriver: {str(e)}")
                    raise
                finally:
                    try:
                        driver.quit()
                    except:
                        pass  # Ignore errors during cleanup
            
            content = await asyncio.to_thread(fetch_with_uc)
        else:
            # Fallback to cloudscraper (may not work for Forbes)
            logger.warning("undetected_chromedriver not available, using cloudscraper (may fail)...")
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=3
            )
            
            # Try to fetch with cloudscraper
            response = await asyncio.to_thread(scraper.get, url, timeout=90)
            if response.status_code != 200:
                logger.error(f"Cloudscraper failed with status {response.status_code}")
                return []
            content = response.content
        
        logger.debug(f"Received {len(content)} bytes from sitemap")
        
        # Check if response is HTML (Access Denied page) instead of XML
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html') or b'Access Denied' in content or b'AccessDenied' in content or b'<iframe' in content:
            logger.error(f"Forbes returned Access Denied/Challenge page instead of XML sitemap")
            logger.debug(f"Response content (first 500 chars): {content[:500].decode('utf-8', errors='ignore')}")
            return []
        
        # Try to parse XML
        # If content is HTML (from undetected_chromedriver), extract XML from it
        if b'<urlset' in content:
            # Find the XML part (might be embedded in HTML)
            xml_start = content.find(b'<urlset')
            if xml_start > 0:
                # Extract just the XML part
                xml_end = content.find(b'</urlset>') + len(b'</urlset>')
                if xml_end > xml_start:
                    content = content[xml_start:xml_end]
        
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {str(e)}")
            logger.debug(f"First 500 chars of response: {content[:500].decode('utf-8', errors='ignore')}")
            return []
        
        articles = []
        # Find all URL entries - try both with and without namespace
        url_entries = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        if not url_entries:
            # Try without namespace prefix
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
                
                # Try to find news:news element
                news_element = url_entry.find('.//{http://www.google.com/schemas/sitemap-news/0.9}news')
                pub_date = None
                
                # Extract publication date from news:news element
                if news_element is not None:
                    pub_date_element = news_element.find('.//{http://www.google.com/schemas/sitemap-news/0.9}publication_date')
                    if pub_date_element is not None and pub_date_element.text:
                        pub_date = pub_date_element.text
                
                # Fallback to lastmod if no publication date
                if not pub_date:
                    lastmod_element = url_entry.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    if lastmod_element is None:
                        lastmod_element = url_entry.find('.//lastmod')
                    if lastmod_element is not None and lastmod_element.text:
                        pub_date = lastmod_element.text
                
                articles.append({
                    'url': url_text,
                    'lastmod': pub_date
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
    
    # Use word boundary matching to avoid false positives (e.g., "ai" in "raises")
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    return has_ai and has_funding

async def extract_and_filter_paragraphs(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs and title from a Forbes article URL."""
    async with semaphore:
        try:
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            
            root = html.fromstring(response.text)
            
            # Extract title
            title = ""
            title_selectors = [
                "//h1",
                "//title",
                "//meta[@property='og:title']/@content",
                "//article//h1",
                "//header//h1"
            ]
            
            for selector in title_selectors:
                title_nodes = root.xpath(selector)
                if title_nodes:
                    if isinstance(title_nodes[0], str):
                        title = title_nodes[0]
                    else:
                        title = title_nodes[0].text_content().strip()
                    if title:
                        break
            
            # Extract paragraphs - try multiple selectors
            # Priority order: article-body div first (primary structure), then fallbacks
            paragraphs = []
            
            # Method 1: Extract from article-body-container or article-body div (primary structure for Forbes)
            # Structure: <div class="b6Cr_ article-body-container"><div class="fs-article fs-responsive-text current-article article-body"> with <p> tags
            article_body_container = root.xpath("//div[contains(@class, 'article-body-container')]//div[contains(@class, 'article-body')] | //div[contains(@class, 'article-body')]")
            if article_body_container:
                # Get all p tags within article-body
                all_p_tags = article_body_container[0].xpath(".//p")
                
                paragraphs = []
                for p_tag in all_p_tags:
                    # Skip empty paragraphs, author attribution, and newsletter forms
                    text = p_tag.text_content().strip()
                    
                    # Filter out unwanted content
                    skip_texts = [
                        'Abhi Sharma', 'Forbes Technology Council', 'Forbes Daily', 
                        'Sign Up', 'Email Address', 'By signing up', 'Editorial Standards',
                        'Reprints & Permissions', 'MORE FOR YOU', 'PROMOTED'
                    ]
                    
                    # Check if paragraph is inside unwanted containers (ads, newsletters, etc.)
                    parent = p_tag.getparent()
                    skip_paragraph = False
                    while parent is not None:
                        if parent.tag == 'div':
                            parent_class = parent.get('class', '')
                            if isinstance(parent_class, list):
                                parent_class = ' '.join(parent_class)
                            # Skip paragraphs in newsletter, ad, or promotional sections
                            if any(unwanted in parent_class.lower() for unwanted in ['newsletter', 'vestpocket', 'promoted', 'recirc', 'ad-container']):
                                skip_paragraph = True
                                break
                        parent = parent.getparent()
                    
                    # Filter out very short paragraphs, author bio lines, and unwanted content
                    if (not skip_paragraph and text and len(text) > 50 and 
                        not any(skip in text for skip in skip_texts)):
                        paragraphs.append(text)
            
            # Method 2: Standard article content selectors (fallback)
            if not paragraphs:
                p_selectors = [
                    "//div[contains(@class, 'article-content')]//p",
                    "//div[contains(@class, 'entry-content')]//p",
                    "//div[contains(@class, 'post-content')]//p",
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

async def fetch_forbes_data() -> Dict[str, List[str]]:
    """
    Main function to fetch Forbes data.

    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)

    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from Forbes...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Parse sitemap to get all article URLs with dates
            all_articles = await parse_sitemap(client, SITEMAP_URL)
            
            if not all_articles:
                logger.warning("No articles found in sitemap")
                return {"urls": [], "paragraphs": []}
            
            logger.info(f"Found {len(all_articles)} total articles in sitemap")
            
            # Step 2: Filter articles by date (last 2 months)
            recent_articles = [
                article for article in all_articles
                if is_within_last_two_months(article.get('lastmod'))
            ]
            
            logger.info(f"Found {len(recent_articles)} articles from last 2 months")
            
            # Step 3: Extract content and filter by AI funding keywords
            results = {"urls": [], "paragraphs": []}
            semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
            
            tasks = [extract_and_filter_paragraphs(client, article['url'], semaphore) for article in recent_articles]
            
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs, title = await coroutine
                if paragraphs and title:
                    # Check if content is AI funding related
                    content_text = '\n'.join(paragraphs)
                    if is_ai_funding_related_content(title, content_text):
                        # Store URL and paragraphs - they are paired by index
                        results["urls"].append(url)
                        results["paragraphs"].append(content_text)
                        logger.info(f"✅ Matched AI funding article: {url}")
            
            logger.info(f"Found {len(results['urls'])} AI funding articles from last 2 months")
            logger.info("Done fetching data from Forbes")
            return results
            
    except Exception as e:
        logger.exception(f"Error fetching/parsing Forbes data: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_forbes_data()

    llm_results = None

    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        # Log what's being passed to LLM for verification
        num_urls = len(links_and_paragraphs.get("urls", []))
        num_paragraphs = len(links_and_paragraphs.get("paragraphs", []))
        logger.info(f"Passing {num_urls} URLs and {num_paragraphs} paragraph contents to AI extraction")
        if num_paragraphs > 0:
            # Log first paragraph sample to verify content is being extracted
            first_paragraph = links_and_paragraphs.get("paragraphs", [])[0]
            logger.debug(f"First paragraph sample (first 200 chars): {first_paragraph[:200]}...")
        
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)

            if result:
                llm_results = copy.deepcopy(funding_data_dict)
                llm_results["company_name"] = result.get("company_name", [])
                llm_results["amount_raised"] = result.get("amount_raised", [])
                llm_results["funding_round"] = result.get("funding_round", [])
                llm_results["investor_companies"] = result.get("investor_companies", [])
                llm_results["investor_people"] = result.get("investor_people", [])
                llm_results["company_decision_makers"] = result.get("company_decision_makers", [])
                llm_results["company_decision_makers_position"] = result.get("company_decision_makers_position", [])
                llm_results["city"] = result.get("city", [])
                llm_results["country"] = result.get("country", [])
                llm_results["article_date"] = result.get("article_date", [])
                llm_results["tags"] = result.get("tags", [])

                # Ensure source is a list matching the number of companies
                num_companies = len(result.get("company_name", []))
                llm_results["source"] = ["Forbes"] * num_companies

                # Store source URLs - these correspond to the paragraphs that were processed
                source_urls = links_and_paragraphs.get("urls", [])
                llm_results["link"] = source_urls

                if source_urls:
                    logger.info(f"Source URLs tracked: {len(source_urls)} URLs mapped to {num_companies} extracted companies")
                    logger.debug(f"First few source URLs: {source_urls[:3]}")

                llm_results["type"] = "funding"
            else:
                logger.warning("AI extraction for Forbes returned no data")

        except Exception as e:
            logger.error(f"Failed to extract AI content from Forbes data: {str(e)}")
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")

    duration = time.perf_counter() - start_time
    logger.info(f"Forbes took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())

