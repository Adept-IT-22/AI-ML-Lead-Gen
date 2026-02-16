# This file fetches AI funding news from Tech Funding News

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

# Sitemap index URL
SITEMAP_INDEX_URL = "https://techfundingnews.com/sitemap_index.xml"

# Relevant sitemap patterns for funding news
RELEVANT_SITEMAP_PATTERNS = [
    'post-sitemap'
]

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
            # Handle negative timezone like -05:00 (need to find the timezone part)
            # Look for pattern like "T12:01:00-05:00" or "T12:01-05:00"
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
            "%Y-%m-%dT%H:%M:%S",    # Without timezone
            "%Y-%m-%dT%H:%M",       # Without timezone, no seconds
            "%Y-%m-%d",             # Date only
        ]
        
        article_date = None
        for fmt in date_formats:
            try:
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

async def parse_sitemap_index(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse sitemap index and return relevant child sitemap URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap index: {url}")
    
    try:
        response = await client.get(url)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        
        # Get all sitemap entries with their lastmod dates
        sitemap_entries = []
        for sitemap in root.findall('sitemap:sitemap', NAMESPACE):
            loc_element = sitemap.find('sitemap:loc', NAMESPACE)
            lastmod_element = sitemap.find('sitemap:lastmod', NAMESPACE)
            
            if loc_element is not None and loc_element.text:
                sitemap_url = loc_element.text
                # Filter to relevant sitemaps (post-sitemap files)
                if sitemap_url != "https://techfundingnews.com/post-sitemap.xml" and any(pattern in sitemap_url for pattern in RELEVANT_SITEMAP_PATTERNS):
                    lastmod = lastmod_element.text if lastmod_element is not None else None
                    sitemap_entries.append({
                        'url': sitemap_url,
                        'lastmod': lastmod
                    })
        
        logger.info(f"Found {len(sitemap_entries)} relevant sitemaps out of total")
        return sitemap_entries
        
    except Exception as e:
        logger.error(f"Error parsing sitemap index {url}: {str(e)}")
        return []

async def parse_sitemap(client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
    """Parse a sitemap XML and extract URLs with their lastmod dates."""
    logger.info(f"Parsing sitemap: {url}")
    
    try:
        response = await client.get(url)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)

        articles = []
        for url_entry in root.findall('ns:url', NAMESPACE):
            loc_element = url_entry.find('ns:loc', NAMESPACE)
            lastmod_element = url_entry.find('ns:lastmod', NAMESPACE)
            
            if loc_element is not None and loc_element.text:
                url_text = loc_element.text
                lastmod_text = lastmod_element.text if lastmod_element is not None else None
                
                if is_ai_funding_related_content(url_text):
                    articles.append({
                        'url': url_text,
                        'lastmod': lastmod_text
                    })
        
        logger.info(f"Extracted {len(articles)} URLs from {url}")
        return articles
        
    except Exception as e:
        logger.error(f"Error parsing sitemap {url}: {str(e)}")
        return []

def is_ai_funding_related_content(url: str) -> bool:
    """Check if article content is related to AI funding."""
    text = url.lower()
    
    ai_keywords = ['ai', 'ai' 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 
                   'neural network', 'llm', 'large language model', 'genai', 'generative ai']
    
    funding_keywords = FUNDING_KEYWORDS  
    
    # Use word boundary matching for AI keywords to avoid false positives
    has_ai = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in ai_keywords)
    has_funding = any(keyword in text for keyword in funding_keywords)
    
    if has_ai and has_funding: 
        logger.info(f"✅ Matched AI funding article: {url}")
        return True

    return False

async def extract_and_filter_paragraphs(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, List[str], str]:
    """Extract paragraphs and title from a Tech Funding News article URL."""
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
            
            # Extract paragraphs - prioritize entry-content div
            paragraphs = []
            
            # Method 1: Extract from entry-content div (primary structure for Tech Funding News)
            # Structure: <div class="entry-content"> with <p> tags
            entry_content_container = root.xpath("//div[contains(@class, 'entry-content')]")
            if entry_content_container:
                # Get all p tags within entry-content
                all_p_tags = entry_content_container[0].xpath(".//p")
                
                paragraphs = []
                for p_tag in all_p_tags:
                    text = p_tag.text_content().strip()
                    if text and len(text) > 50:
                        paragraphs.append(text)
            
            # Method 2: Standard article content selectors (fallback)
            if not paragraphs:
                p_selectors = [
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

async def fetch_techfundingnews_data() -> Dict[str, List[str]]:
    """
    Main function to fetch Tech Funding News data.

    Returns:
        Dict with keys:
        - "urls": List of source URLs (one per article)
        - "paragraphs": List of paragraph content (one per article)

    Note: URLs and paragraphs are paired by index:
        - results["urls"][i] corresponds to results["paragraphs"][i]
        - Each paragraph entry comes from the URL at the same index
    """
    logger.info("Fetching data from Tech Funding News...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Parse sitemap index to get all post-sitemap URLs with their lastmod dates
            sitemap_entries = await parse_sitemap_index(client, SITEMAP_INDEX_URL)
            
            if not sitemap_entries:
                logger.warning("No relevant sitemaps found")
                return {"urls": [], "paragraphs": []}
            
            # Step 2: Filter sitemaps by their lastmod date (only parse sitemaps updated in last 2 months)
            recent_sitemaps = [
                entry for entry in sitemap_entries
                if is_within_last_two_months(entry.get('lastmod'))
            ]
            
            logger.info(f"Filtered to {len(recent_sitemaps)} recent sitemaps (last 2 months) out of {len(sitemap_entries)} total")
            
            if not recent_sitemaps:
                logger.warning("No recent sitemaps found (last 2 months)")
                return {"urls": [], "paragraphs": []}
            
            # Step 3: Parse all recent sitemaps to get articles with dates
            all_articles = []
            tasks = [parse_sitemap(client, entry['url']) for entry in recent_sitemaps]
            
            for coroutine in asyncio.as_completed(tasks):
                articles = await coroutine
                all_articles.extend(articles)
            
            logger.info(f"Found {len(all_articles)} total articles across {len(recent_sitemaps)} recent sitemaps")
            
            # Step 4: Filter articles by date (last 2 months)
            recent_articles = [
                article for article in all_articles
                if is_within_last_two_months(article.get('lastmod'))
            ]
            
            logger.info(f"Found {len(recent_articles)} articles from last 2 months")
            
            # Step 5: Extract content and filter by AI funding keywords
            recent_articles = recent_articles[:5]
            results = {"urls": [], "paragraphs": []}
            semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
            
            tasks = [extract_and_filter_paragraphs(client, article['url'], semaphore) for article in recent_articles]
            
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs, title = await coroutine
                if paragraphs and title:
                    # Store URL and paragraphs - they are paired by index
                    results["urls"].append(url)
                    results["paragraphs"].append(paragraphs)
                    
            
            logger.info(f"Found {len(results['urls'])} AI funding articles from last 2 months")
            logger.info("Done fetching data from Tech Funding News")
            return results
            
    except Exception as e:
        logger.exception(f"Error fetching/parsing Tech Funding News data: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def main():
    start_time = time.perf_counter()
    
    links_and_paragraphs = await fetch_techfundingnews_data()
    
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
                
                # Explicitly copy each field from AI extraction result (like Forbes)
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
                llm_results["source"] = ["Tech Funding News"] 
                
                # Store source URLs - these correspond to the paragraphs that were processed
                source_urls = links_and_paragraphs.get("urls", [])
                llm_results["link"] = source_urls
                
                # Log source URL tracking for verification
                if source_urls:
                    logger.info(f"Source URLs tracked: {len(source_urls)} URLs mapped to {num_companies} extracted companies")
                    logger.debug(f"First few source URLs: {source_urls[:3]}")
                
            else:
                logger.warning("AI extraction for Tech Funding News returned no data")
                
        except Exception as e:
            logger.error(f"Failed to extract AI content from Tech Funding News data: {str(e)}")
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")
    
    duration = time.perf_counter() - start_time
    logger.info(f"Tech Funding News took {duration:.2f} seconds")
    
    if llm_results is None:
        return copy.deepcopy(funding_data_dict)
    
    return llm_results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

