# This file fetches AI funding news from CB Insights

import copy
import re
import time
import asyncio
import logging
import cloudscraper
from datetime import datetime
from lxml import etree, html
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

# CB Insights sitemap structure
URL = "https://www.cbinsights.com/research/sitemap.xml"
FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding', 'invests', 'series', 'round', 'seed', 'venture', 'capital']

# Configure semaphore for rate limiting
MAX_CONNECTIONS = 10

# Namespace for XML parsing
NAMESPACE = {
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
}

async def fetch_sync(client: cloudscraper.CloudScraper, url: str):
    """Run blocking cloudscraper.get in a thread."""
    return await asyncio.to_thread(client.get, url)

async def find_latest_sitemaps(client: cloudscraper.CloudScraper) -> List[str]:
    """
    Parse the main sitemap index and find the latest sub-sitemaps.
    Returns the last 2 months (October and November) plus any sitemaps updated recently.
    """
    logger.info("Fetching latest sitemaps from CB Insights...")
    
    try:
        response = await fetch_sync(client, URL)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        
        # Get current date for filtering
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Find all sub-sitemap URLs with their last modified dates
        sitemap_urls = []
        for sitemap in root.findall('ns:sitemap', NAMESPACE):
            loc_element = sitemap.find('ns:loc', NAMESPACE)
            lastmod_element = sitemap.find('ns:lastmod', NAMESPACE)
            
            if loc_element is not None and loc_element.text:
                sitemap_url = loc_element.text
                # Only process post sitemaps (exclude misc and page sitemaps)
                if 'sitemap-pt-post' in sitemap_url:
                    lastmod = lastmod_element.text if lastmod_element is not None else None
                    sitemap_urls.append((sitemap_url, sitemap, lastmod))
        
        # Extract date from sitemap URL
        # Format: sitemap-pt-post-2025-11.xml
        date_pattern = re.compile(r'sitemap-pt-post-(\d{4})-(\d{2})\.xml')
        
        dated_sitemaps = []
        for sitemap_url, sitemap_elem, lastmod in sitemap_urls:
            match = date_pattern.search(sitemap_url)
            if match:
                year, month = int(match.group(1)), int(match.group(2))
                
                # Check if this is last 2 months
                is_last_2_months = (
                    (year == current_year and month in [current_month - 1, current_month])
                )
                
                # Check if sitemap was updated recently (within last 60 days)
                recently_updated = False
                if lastmod:
                    try:
                        # Parse ISO format date (e.g., "2025-11-04T02:25:17+00:00")
                        lastmod_str = lastmod.replace('Z', '+00:00')
                        if '+' in lastmod_str:
                            lastmod_date = datetime.fromisoformat(lastmod_str)
                        else:
                            lastmod_date = datetime.fromisoformat(lastmod_str + '+00:00')
                        
                        # Calculate days difference (handle timezone-aware datetime)
                        if lastmod_date.tzinfo:
                            lastmod_naive = lastmod_date.replace(tzinfo=None)
                        else:
                            lastmod_naive = lastmod_date
                        
                        days_ago = (current_date - lastmod_naive).days
                        if days_ago <= 60 and days_ago >= 0:
                            recently_updated = True
                    except Exception as e:
                        logger.debug(f"Could not parse lastmod date '{lastmod}': {e}")
                        pass
                
                if is_last_2_months or recently_updated:
                    dated_sitemaps.append((year, month, sitemap_url, lastmod))
        
        # Sort by date descending
        dated_sitemaps.sort(reverse=True, key=lambda x: (x[0], x[1]))
        
        selected_sitemaps = [url for _, _, url, _ in dated_sitemaps]
        
        logger.info(f"Found {len(selected_sitemaps)} sitemaps to process (last 2 months + recently updated)")
        if dated_sitemaps:
            logger.info(f"Processing sitemaps from {dated_sitemaps[-1][:2]} to {dated_sitemaps[0][:2]}")
        return selected_sitemaps
        
    except Exception as e:
        logger.exception(f"Error fetching/parsing main sitemap {URL}: {str(e)}")
        return []

async def fetch_ai_funding_articles(client: cloudscraper.CloudScraper, sitemap_url: str) -> List[str]:
    """
    Parse a sub-sitemap and extract AI funding-related article URLs.
    """
    logger.info(f"Fetching articles from {sitemap_url}...")
    
    try:
        response = await fetch_sync(client, sitemap_url)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        
        article_links = []
        for url in root.findall('ns:url', NAMESPACE):
            loc_element = url.find('ns:loc', NAMESPACE)
            if loc_element is not None and loc_element.text:
                article_link = loc_element.text
                link_lower = article_link.lower()
                
                # Filter for AI-related articles - include if has AI keywords OR funding keywords
                # We're looking for AI funding news, so articles with AI keywords are likely relevant
                # even if funding keywords aren't in URL (they may be in content)
                has_ai = ('-ai' in link_lower or 'ai-' in link_lower or 'artificial-intelligence' in link_lower or 
                          'artificialintelligence' in link_lower or 'machine-learning' in link_lower or
                          'genai' in link_lower or 'generative-ai' in link_lower)
                has_funding = any(keyword in link_lower for keyword in FUNDING_KEYWORDS)
                
                # Include articles with AI keywords (they may discuss funding in content)
                # OR articles with funding keywords (they may be about AI companies)
                if has_ai and has_funding:
                        article_links.append(article_link)
        
        logger.info(f"Found {len(article_links)} AI funding articles in {sitemap_url}")
        return article_links
        
    except Exception as e:
        logger.exception(f"Error fetching/parsing sub-sitemap {sitemap_url}: {str(e)}")
        return []

async def fetch_cbinsights_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from CB Insights...")
    
    try:
        client = cloudscraper.create_scraper()
        
        # Get latest sitemaps
        latest_sitemaps = await find_latest_sitemaps(client)
        if not latest_sitemaps:
            logger.warning("No sitemaps found")
            return {"urls": [], "paragraphs": []}
        
        # Collect all article links from all sitemaps
        # Process sitemaps in batches to avoid overwhelming the server
        all_article_links = []
        batch_size = 10
        
        logger.info(f"Processing {len(latest_sitemaps)} sitemaps in batches of {batch_size}...")
        for i in range(0, len(latest_sitemaps), batch_size):
            batch = latest_sitemaps[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(latest_sitemaps) + batch_size - 1)//batch_size} ({len(batch)} sitemaps)...")
            
            # Process batch in parallel
            tasks = [fetch_ai_funding_articles(client, sitemap_url) for sitemap_url in batch]
            batch_results = await asyncio.gather(*tasks)
            
            for articles in batch_results:
                all_article_links.extend(articles)
            
            logger.info(f"Batch complete. Total articles found so far: {len(all_article_links)}")
        
        # Remove duplicates
        all_article_links = list(set(all_article_links))
        logger.info(f"Found {len(all_article_links)} total relevant articles from CB Insights")
        
        if not all_article_links:
            return {"urls": [], "paragraphs": []}
        
        # Extract paragraphs from each article
        semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
        results = {"urls": [], "paragraphs": []}
        tasks = [extract_paragraphs(client, url, semaphore) for url in all_article_links]
        
        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine
            if paragraphs:
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))
        
        logger.info("Done fetching data from CB Insights")
        return results
        
    except Exception as e:
        logger.exception(f"Error fetching data from CB Insights: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str, semaphore: asyncio.Semaphore) -> tuple[str, List[str]]:
    async with semaphore:
        logger.info(f"Fetching paragraphs from {url}...")
        try:
            response = await fetch_sync(client, url)
            response.raise_for_status()
            
            root = html.fromstring(response.text)
            
            # CB Insights article structure - target the article-content container
            # Based on the HTML structure: <div class="article-content container">
            paragraph_selectors = [
                "//div[contains(@class, 'article-content')]//p",
                "//div[contains(@class, 'article-content')]//div[contains(@class, 'container')]//p",
                "//article//p",
                "//div[contains(@class, 'post-content')]//p",
                "//main//p",
            ]
            
            paragraphs = []
            for selector in paragraph_selectors:
                paragraph_nodes = root.xpath(selector)
                if paragraph_nodes:
                    paragraphs = [
                        node.text_content().strip() 
                        for node in paragraph_nodes 
                        if node.text_content().strip() and len(node.text_content().strip()) > 20
                    ]
                    if paragraphs:
                        break
            
            # If no paragraphs found, try a more general approach
            if not paragraphs:
                all_paragraphs = root.xpath("//p")
                paragraphs = [
                    node.text_content().strip() 
                    for node in all_paragraphs 
                    if node.text_content().strip() and len(node.text_content().strip()) > 20
                ]
            
            logger.info(f"Extracted {len(paragraphs)} paragraphs from {url}")
            return url, paragraphs
            
        except Exception as e:
            logger.exception(f"Failed to fetch paragraphs from {url}: {str(e)}")
        
        return url, []

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_cbinsights_data()
    
    llm_results = None
    
    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
            
            if result:
                llm_results = copy.deepcopy(funding_data_dict)
                
                for key, value_list in result.items():
                    if key in llm_results and isinstance(value_list, list):
                        llm_results[key].extend(value_list)
                    elif key in llm_results:
                        llm_results[key] = value_list
                
                # Ensure source is a list 
                llm_results["source"] = ["CB Insights"] 
                llm_results["link"] = links_and_paragraphs.get("urls")
                
            else:
                logger.warning("AI extraction for CB Insights returned no data")
                
        except Exception as e:
            logger.error(f"Failed to extract AI content from CB Insights data: {str(e)}")
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")
    
    duration = time.perf_counter() - start_time
    logger.info(f"CB Insights took {duration:.2f} seconds")
    
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())

