# This file fetches AI funding news from PitchBook

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

# Sitemap index URL
SITEMAP_INDEX_URL = "https://pitchbook.com/sitemap.xml"

# Relevant sitemap patterns for funding news
RELEVANT_SITEMAP_PATTERNS = [
    'press-release',
    'na-newsletter'
]

FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding', 'investment', 'funded']

# Configure semaphore for rate limiting
MAX_CONNECTIONS = 10

# XML namespaces
NAMESPACE = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
}

async def fetch_sync(client: cloudscraper.CloudScraper, url: str):
    """Run blocking cloudscraper.get in a thread."""
    return await asyncio.to_thread(client.get, url)

async def fetch_gz_with_scraper(client: cloudscraper.CloudScraper, url: str) -> bytes:
    """Fetch .gz file using cloudscraper (handles anti-bot protection)."""
    response = await asyncio.to_thread(client.get, url)
    response.raise_for_status()
    return response.content

async def parse_sitemap_index(client: cloudscraper.CloudScraper, url: str) -> List[str]:
    """Parse sitemap index and return relevant child sitemap URLs."""
    logger.info(f"Parsing sitemap index: {url}")
    
    try:
        response = await fetch_sync(client, url)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        
        # Get all sitemap URLs from index
        sitemap_urls = root.xpath("//sitemap:loc/text()", namespaces=NAMESPACE)
        
        # Filter to relevant sitemaps
        relevant_urls = [
            url for url in sitemap_urls 
            if any(pattern in url for pattern in RELEVANT_SITEMAP_PATTERNS)
        ]
        
        logger.info(f"Found {len(relevant_urls)} relevant sitemaps out of {len(sitemap_urls)} total")
        return relevant_urls
        
    except Exception as e:
        logger.error(f"Error parsing sitemap index {url}: {str(e)}")
        return []

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

async def parse_decompressed_sitemap(xml_content: bytes) -> List[Dict[str, str]]:
    """Parse decompressed XML and extract URLs with their lastmod dates."""
    logger.info("Parsing decompressed sitemap...")
    
    try:
        root = etree.fromstring(xml_content)
        
        articles = []
        for url_entry in root.findall('ns:url', NAMESPACE):
            loc_element = url_entry.find('ns:loc', NAMESPACE)
            lastmod_element = url_entry.find('ns:lastmod', NAMESPACE)
            
            if loc_element is not None and loc_element.text:
                url_text = loc_element.text
                lastmod_text = lastmod_element.text if lastmod_element is not None else None
                
                articles.append({
                    'url': url_text,
                    'lastmod': lastmod_text
                })
        
        logger.info(f"Extracted {len(articles)} URLs from sitemap")
        return articles
        
    except Exception as e:
        logger.error(f"Error parsing decompressed sitemap: {str(e)}")
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
    import re
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    return has_ai and has_funding

def is_within_last_two_months(lastmod_str: Optional[str]) -> bool:
    """Check if lastmod date is within the last 2 months (60 days)."""
    if not lastmod_str:
        # If no date, include it (fallback to be safe)
        return True
    
    try:
        # Parse ISO format date (e.g., "2025-11-05T07:24:35.003+00:00")
        lastmod_str_clean = lastmod_str.replace('Z', '+00:00')
        if '+' in lastmod_str_clean:
            lastmod_date = datetime.fromisoformat(lastmod_str_clean)
        else:
            lastmod_date = datetime.fromisoformat(lastmod_str_clean + '+00:00')
        
        # Calculate days difference
        current_date = datetime.now()
        if lastmod_date.tzinfo:
            lastmod_naive = lastmod_date.replace(tzinfo=None)
        else:
            lastmod_naive = lastmod_date
        
        days_ago = (current_date - lastmod_naive).days
        
        # Include articles from last 60 days
        return 0 <= days_ago <= 60
        
    except Exception as e:
        logger.debug(f"Could not parse lastmod date '{lastmod_str}': {e}")
        # If we can't parse the date, include it anyway (fallback)
        return True

async def fetch_pitchbook_data() -> Dict[str, List[str]]:
    """
    Main function to fetch PitchBook data.
    
    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)
        
    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from PitchBook...")
    
    try:
        # Use cloudscraper for sitemap index (handles anti-bot protection)
        scraper_client = cloudscraper.create_scraper()
        
        # Step 1: Parse sitemap index
        relevant_sitemap_urls = await parse_sitemap_index(scraper_client, SITEMAP_INDEX_URL)
        
        if not relevant_sitemap_urls:
            logger.warning("No relevant sitemaps found")
            return {"urls": [], "paragraphs": []}
        
        # Step 2: Download, decompress, and parse all relevant sitemaps
        all_articles = []
        for sitemap_url in relevant_sitemap_urls:
            decompressed_content = await fetch_and_decompress_gz(scraper_client, sitemap_url)
            if decompressed_content:
                articles = await parse_decompressed_sitemap(decompressed_content)
                all_articles.extend(articles)
                
                # Small delay between sitemap fetches
                await asyncio.sleep(1)
        
        logger.info(f"Total articles found across all sitemaps: {len(all_articles)}")
        
        # Step 3: Filter by date first (last 2 months)
        recent_articles = []
        for article in all_articles:
            url = article['url']
            lastmod = article.get('lastmod')
            
            if is_within_last_two_months(lastmod):
                recent_articles.append(url)
        
        logger.info(f"Found {len(recent_articles)} articles from last 2 months")
        
        # Step 4: Fetch content and filter by AI funding keywords in content
        semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
        results = {"urls": [], "paragraphs": []}
        
        tasks = [extract_and_filter_paragraphs(scraper_client, url, semaphore) for url in recent_articles]
        
        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs, title = await coroutine
            if paragraphs and title:
                # Check if content is AI funding related
                content_text = '\n'.join(paragraphs)
                if is_ai_funding_related_content(title, content_text):
                    # Store URL and paragraphs - they are paired by index
                    # results["urls"][i] corresponds to results["paragraphs"][i]
                    results["urls"].append(url)
                    results["paragraphs"].append(content_text)
                    logger.info(f"✅ Matched AI funding article: {url} (Source: {url})")
        
        logger.info(f"Found {len(results['urls'])} AI funding articles from last 2 months")
        logger.info("Done fetching data from PitchBook")
        return results
            
    except Exception as e:
        logger.exception(f"Error fetching/parsing PitchBook data: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def extract_and_filter_paragraphs(client: cloudscraper.CloudScraper, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs and title from a PitchBook article URL."""
    async with semaphore:
        try:
            response = await fetch_sync(client, url)
            response.raise_for_status()
            
            root = html.fromstring(response.text)
            
            # Extract title
            title = ""
            title_selectors = [
                "//h1",
                "//title",
                "//meta[@property='og:title']/@content",
                "//article//h1"
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
            
            # Try multiple extraction methods for PitchBook articles
            # Priority order: Newsletter format first (most common), then press releases/articles
            paragraphs = []
            
            # Method 1: Extract from <span> tags in nb-content div (newsletter format)
            # Used by: /newsletter/ URLs (VC deals, PE deals, fundraising, exit-IPO, etc.)
            # Structure: article__content -> newsletter-box -> nb-content -> span
            span_content_nodes = root.xpath("//div[contains(@class, 'nb-content')]//span")
            if span_content_nodes:
                # Get HTML content to preserve <br><br> separators
                html_content = html.tostring(span_content_nodes[0], encoding='unicode', method='html')
                
                # Split on <br><br> or <br />\s*<br /> patterns
                # Handle both <br><br> and <br />\n<br /> variants
                parts = re.split(r'<br\s*/?>\s*(?:<br\s*/?>)', html_content, flags=re.IGNORECASE)
                
                if len(parts) > 1:
                    # Parse each part as HTML and extract text
                    paragraphs = []
                    for part in parts:
                        try:
                            # Wrap in a div to ensure valid HTML
                            part_html = f"<div>{part}</div>"
                            part_root = html.fromstring(part_html)
                            text = part_root.text_content().strip()
                            # Remove extra whitespace and clean up
                            text = re.sub(r'\s+', ' ', text).strip()
                            if text and len(text) > 50:
                                paragraphs.append(text)
                        except Exception:
                            # If parsing fails, try simple text extraction
                            text = re.sub(r'<[^>]+>', '', part).strip()
                            text = re.sub(r'\s+', ' ', text).strip()
                            if text and len(text) > 50:
                                paragraphs.append(text)
                else:
                    # Fallback: split on double newlines in text content
                    full_text = span_content_nodes[0].text_content()
                    parts = re.split(r'\n\s*\n+', full_text)
                    paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
            
            # Method 2: Extract from newsletter-box div (alternative newsletter format)
            # Some newsletter variations might use different structures
            if not paragraphs:
                newsletter_box_nodes = root.xpath("//div[contains(@class, 'newsletter-box')]//div[contains(@class, 'nb-content')]")
                if newsletter_box_nodes:
                    # Try to extract from nested elements
                    for box_node in newsletter_box_nodes:
                        # Look for text content or nested elements
                        text_content = box_node.text_content()
                        if text_content and len(text_content) > 100:
                            # Split on double line breaks or <br> tags
                            parts = re.split(r'\n\s*\n+|<br\s*/?>', text_content)
                            paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
                            if paragraphs:
                                break
            
            # Method 3: Standard <p> tags (for press releases and regular articles)
            # Used by: /press-release/ URLs and other article formats
            if not paragraphs:
                p_selectors = [
                    "//div[contains(@class, 'article__content')]//p",
                    "//article//p",
                    "//div[contains(@class, 'article')]//p",
                    "//div[contains(@class, 'content')]//p",
                    "//main//p",
                    "//div[contains(@class, 'post-content')]//p",
                    "//div[contains(@class, 'press-release')]//p",
                    "//div[contains(@class, 'press')]//p"
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
            
            # Method 4: Extract from article__content div (direct text extraction)
            # Fallback for articles without clear paragraph structure
            if not paragraphs:
                article_content_nodes = root.xpath("//div[contains(@class, 'article__content')]")
                if article_content_nodes:
                    full_text = article_content_nodes[0].text_content()
                    # Split on double line breaks
                    parts = re.split(r'\n\s*\n+', full_text)
                    paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
            
            # Method 5: Extract from any div with article-related classes
            # Broad fallback for various article structures
            if not paragraphs:
                article_divs = root.xpath("//div[contains(@class, 'article') or contains(@class, 'content')]")
                for div in article_divs:
                    # Get all text nodes and split intelligently
                    text_content = div.text_content()
                    if text_content and len(text_content) > 100:
                        # Split on multiple newlines or <br> tags
                        parts = re.split(r'\n\s*\n+|<br\s*/?>', text_content)
                        paragraphs = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
                        if paragraphs:
                            break
            
            # Method 6: Fallback - get all paragraphs from entire page
            # Last resort for edge cases
            if not paragraphs:
                paragraph_nodes = root.xpath("//p")
                paragraphs = [
                    node.text_content().strip() 
                    for node in paragraph_nodes 
                    if node.text_content().strip() and len(node.text_content().strip()) > 50
                ]
            
            return url, paragraphs, title
            
        except Exception as e:
            logger.debug(f"Failed to fetch content from {url}: {str(e)}")
        
        return url, [], ""

async def main():
    """Main function to run PitchBook data extraction."""
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_pitchbook_data()
    
    llm_results = None
    
    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
            
            if result:
                llm_results = copy.deepcopy(funding_data_dict)
                
                # Explicitly copy each field from AI extraction result (like Forbes, Tech Funding News)
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
                llm_results["title"] = result.get("title", [])
                
                # Ensure source is a list matching the number of companies
                num_companies = len(result.get("company_name", []))
                llm_results["source"] = ["PitchBook"] * num_companies
                
                # Store source URLs - these correspond to the paragraphs that were processed
                # Each URL in links_and_paragraphs["urls"][i] is the source for paragraphs[i]
                source_urls = links_and_paragraphs.get("urls", [])
                llm_results["link"] = source_urls
                
                # Log source URL tracking for verification
                if source_urls:
                    logger.info(f"Source URLs tracked: {len(source_urls)} URLs mapped to {num_companies} extracted companies")
                    logger.debug(f"First few source URLs: {source_urls[:3]}")
                
                # Add type field for consistency with other sources
                llm_results["type"] = "funding"
            else:
                logger.warning("AI extraction for PitchBook returned no data")
                
        except Exception as e:
            logger.error(f"Failed to extract AI content from PitchBook data: {str(e)}")
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")
    
    duration = time.perf_counter() - start_time
    logger.info(f"PitchBook took {duration:.2f} seconds")
    
    return llm_results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

