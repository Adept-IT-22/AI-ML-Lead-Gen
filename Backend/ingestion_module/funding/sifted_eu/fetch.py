# This file fetches AI funding news from sifted.eu

import copy
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

# Sifted.eu uses a sitemap structure similar to tech.eu
URL = "https://sifted.eu/server-sitemap.xml"
FUNDING_KEYWORDS = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands', 'funding']

# Configure 10 semaphore for rate limiting
MAX_CONNECTIONS = 10

async def fetch_sync(client: cloudscraper.CloudScraper, url: str):
    """Run blocking cloudscraper.get in a thread."""
    return await asyncio.to_thread(client.get, url)

async def fetch_sifted_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from sifted.eu...")
    
    try:
        client = cloudscraper.create_scraper()
        response = await fetch_sync(client, URL)
        response.raise_for_status()

        root = etree.fromstring(response.content)

        # Define XML namespaces
        namespaces = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
        }

        # Get current date for filtering
        current_date = datetime.now()
        
        # Parse article links with date filtering
        article_links = []
        for url_entry in root.findall('ns:url', namespaces):
            loc_element = url_entry.find('ns:loc', namespaces)
            lastmod_element = url_entry.find('ns:lastmod', namespaces)
            
            if loc_element is not None and loc_element.text:
                article_link = loc_element.text
                link_lower = article_link.lower()
                
                # Filter for AI and funding-related articles
                has_ai = ('ai' in link_lower or 'artificial-intelligence' in link_lower)
                has_funding = any(keyword in link_lower for keyword in FUNDING_KEYWORDS)
                
                if has_ai and has_funding:
                    # Check if article is from last 2 months or recently updated
                    is_recent = False
                    
                    if lastmod_element is not None and lastmod_element.text:
                        try:
                            # Parse ISO format date (e.g., "2025-11-04T02:25:17+00:00")
                            lastmod_str = lastmod_element.text.replace('Z', '+00:00')
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
                            # Include articles from last 60 days
                            if days_ago <= 60 and days_ago >= 0:
                                is_recent = True
                        except Exception as e:
                            logger.debug(f"Could not parse lastmod date '{lastmod_element.text}': {e}")
                            # If we can't parse the date, include it anyway (fallback)
                            is_recent = True
                    else:
                        # If no lastmod date, include it (fallback to include all)
                        is_recent = True
                    
                    if is_recent:
                        article_links.append(article_link)

        logger.info(f"Found {len(article_links)} relevant articles from sifted.eu")

        # Extract paragraphs from each article
        semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
        results = {"urls": [], "paragraphs": []}
        tasks = [extract_paragraphs(client, url, semaphore) for url in article_links]

        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine
            if paragraphs:
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

        logger.info("Done fetching data from sifted.eu")
        return results

    except Exception as e:
        logger.exception(f"Error fetching/parsing {URL}: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str, semaphore: asyncio.Semaphore) -> tuple[str, List[str]]:
    async with semaphore:
        logger.info(f"Fetching paragraphs from {url}...")
        try:
            response = await fetch_sync(client, url)
            response.raise_for_status()

            root = html.fromstring(response.text)

            # Target the article__container and get paragraphs with data-block="p"
            paragraph_nodes = root.xpath("//article[contains(@class, 'article__container')]//p[@data-block='p']")
            
            paragraphs = [
                node.text_content().strip() 
                for node in paragraph_nodes 
                if node.text_content().strip()
            ]

            logger.info(f"Extracted {len(paragraphs)} paragraphs from {url}")
            return url, paragraphs

        except Exception as e:
            logger.exception(f"Failed to fetch paragraphs from {url}: {str(e)}")

        return url, []

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_sifted_data()

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

                # Ensure source is a list matching the number of companies
                num_companies = len(result.get("company_name", []))
                llm_results["source"] = ["Sifted.eu"] * num_companies
                llm_results["link"] = links_and_paragraphs.get("urls")
                
                # Add type field for consistency with other sources
                llm_results["type"] = "funding"
            else:
                logger.warning("AI extraction for Sifted.eu returned no data")
                
        except Exception as e:
            logger.error(f"Failed to extract AI content from Sifted.eu data: {str(e)}")
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")

    duration = time.perf_counter() - start_time
    logger.info(f"Sifted.eu took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
