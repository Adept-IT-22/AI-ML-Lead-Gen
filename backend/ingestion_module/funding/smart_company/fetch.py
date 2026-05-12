import copy
import time
import json
import re
import asyncio
import logging
import datetime
import cloudscraper
from lxml import etree, html
from aiolimiter import AsyncLimiter
from lxml.etree import XMLSyntaxError
from typing import Dict, List, Any

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)  

limiter = AsyncLimiter(max_rate=5, time_period=1)

#============URLs==============
URL = ["https://www.smartcompany.com.au/sitemap_index.xml"]

#============KEYWORDS===============
FUNDING_KEYWORDS = ["funding", "raises", "closes", "nets", "secures", "awarded", "notches", "lands", "capital", "seed", "series"] 
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning"]

def compile_keywords_regex(keywords):
    patterns = []
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)
        pattern = r'\b' + escaped_keyword.replace(r'\ ', r'[ -]') + r'\b'
        patterns.append(pattern)
    return re.compile('|'.join(patterns), re.IGNORECASE)


async def fetch_with_cloudscraper(client: cloudscraper.CloudScraper, url: str):
    """Wraps the cloudscraper call with an async rate limiter."""
    async with limiter:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.get(url, timeout=30))
        response.raise_for_status()
        return response

async def fetch_smart_company_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from smartcompany...")

    #=========NAMESPACES=============
    namespaces = {
        "sitemap_ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "n": "http://www.google.com/schemas/sitemap-news/0.9"
    }

    results: Dict[str, List[str]] = {"urls": [], "paragraphs": []}
    article_links = []

    AI_KEYWORDS_REGEX = compile_keywords_regex(AI_KEYWORDS)
    FUNDING_KEYWORDS_REGEX = compile_keywords_regex(FUNDING_KEYWORDS)
  
    client = cloudscraper.create_scraper()
    try:
        # Fetch the main sitemap index to get sub-sitemap URLs
        index_response = await fetch_with_cloudscraper(client, URL[0])
        index_root = etree.fromstring(index_response.content)
        
        latest_sitemap_date = None
        latest_sitemap_url = ''
        highest_sitemap_number = -1 # Used for tie-breaking
        sitemap_pattern = re.compile(r'post-sitemap(\d+)\.xml') 

        # Find the sitemap with the most recent date, using sitemap number as a tie-breaker.
        for sitemap_node in index_root.findall(".//sitemap_ns:sitemap", namespaces):
            loc_el = sitemap_node.find("sitemap_ns:loc", namespaces)
            lastmod_el = sitemap_node.find("sitemap_ns:lastmod", namespaces)

            if loc_el is not None and loc_el.text and "post-sitemap" in loc_el.text and ".xml" in loc_el.text and lastmod_el is not None and lastmod_el.text:
                url_text = loc_el.text
                try:
                    current_date = datetime.datetime.fromisoformat(lastmod_el.text.replace('Z', '+00:00'))
                    
                    match = sitemap_pattern.search(url_text)
                    current_sitemap_number = int(match.group(1)) if match else -1

                    # Prioritize date. If dates are identical, use the sitemap number as a tie-breaker.
                    if latest_sitemap_date is None or current_date > latest_sitemap_date or \
                       (current_date == latest_sitemap_date and current_sitemap_number > highest_sitemap_number):
                        latest_sitemap_date = current_date
                        latest_sitemap_url = url_text
                        highest_sitemap_number = current_sitemap_number

                except ValueError:
                    logger.warning(f"Could not parse date {lastmod_el.text} for sitemap {loc_el.text}")
                    continue

        if not latest_sitemap_url:
            logger.error("Could not find the latest sitemap. Aborting.")
            return {"urls": [], "paragraphs": []}

        logger.info(f"Processing latest sitemap: {latest_sitemap_url}")

        # Process the latest sub-sitemap to find article links
        sub_sitemap_response = await fetch_with_cloudscraper(client, latest_sitemap_url)
        now = datetime.datetime.now(datetime.timezone.utc)
        allowed_months = {now.month, (now - datetime.timedelta(days=30)).month}

        try:
            root = etree.fromstring(sub_sitemap_response.content)
            for url_node in root.findall(".//sitemap_ns:url", namespaces):
                loc_el = url_node.find("sitemap_ns:loc", namespaces)
                date_el = url_node.find("sitemap_ns:lastmod", namespaces)

                if loc_el is not None and loc_el.text and date_el is not None and date_el.text:
                    try:
                        pub_date = datetime.datetime.fromisoformat(date_el.text.replace('Z', '+00:00'))
                        
                        if pub_date.year == now.year and pub_date.month in allowed_months:
                            url_link = loc_el.text
                            if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link):
                                article_links.append(url_link)
                    except (ValueError, TypeError):
                        continue
        except XMLSyntaxError as e:
            logger.error(f"Failed to parse XML from {sub_sitemap_response.url}: {e}")

        # Extract paragraphs from the collected article links
        tasks = [extract_paragraphs(client, url) for url in article_links]
        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine
            if paragraphs:
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

        logger.info(f"Done fetching data from smartcompany. Found {len(results['urls'])} articles.")
        return results

    except Exception as e:
        logger.exception(f"Error fetching/parsing smartcompany sitemaps: {e}")
        return {"urls": [], "paragraphs": []}
    finally:
        client.close()


async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await fetch_with_cloudscraper(client, url)
        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//div[contains(@class, 'entry-content')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content() and node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main() -> Dict[str, Any]:
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_smart_company_data()

    if not (links_and_paragraphs and links_and_paragraphs.get("urls")):
        logger.info("No articles found from smartcompany to process for AI extraction.")
        return copy.deepcopy(funding_data_dict)

    try:
        result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
    except Exception as e:
        logger.error(f"Failed to extract AI content from smartcompany data: {e}")
        result = {}

    if not result:
        logger.warning("AI extraction for smartcompany returned no data. No logging will happen")
        return copy.deepcopy(funding_data_dict)

    llm_results = copy.deepcopy(funding_data_dict)
    for key, value_list in result.items():
        if key in llm_results and isinstance(value_list, list):
            llm_results[key].extend(value_list)
        elif key in llm_results:
            llm_results[key] = value_list

    llm_results["source"].append("smartcompany")
    llm_results["link"] = links_and_paragraphs.get("urls", [])

    duration = time.perf_counter() - start_time
    logger.info(f"smartcompany took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())