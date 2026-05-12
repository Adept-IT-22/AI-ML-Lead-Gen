import copy
import time
import json
import re
import asyncio
import logging
import datetime
import dateparser
import cloudscraper
from lxml import etree, html
from aiolimiter import AsyncLimiter
from typing import Dict, List, Any
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

limiter = AsyncLimiter(max_rate=5, time_period=1)

#============URLs==============
URL = ["https://eu.entrepreneur.com/sitemap_index.xml"]

#============KEYWORDS===============
FUNDING_KEYWORDS = ["funding", "raises", "closes", "nets", "secures", "awarded", "notches", "lands", "seed", "pre-seed", "series"] 
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning", "ai-powered", "genai"]

def compile_keywords_regex(keywords):
    patterns = []
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)
        pattern = r'\b' + escaped_keyword.replace(r'\ ', r'[ -]') + r'\b'
        patterns.append(pattern)
    return re.compile('|'.join(patterns), re.IGNORECASE)


async def fetch_with_cloudscraper(client: cloudscraper.CloudScraper, url: str):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: client.get(url, timeout=30))
    response.raise_for_status()
    return response

async def fetch_eu_entrepreneur_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from eu entrepreneur...")

    results: Dict[str, List[str]] = {"urls": [], "paragraphs": []}
    child_sitemap_urls = []

    AI_KEYWORDS_REGEX = compile_keywords_regex(AI_KEYWORDS)
    FUNDING_KEYWORDS_REGEX = compile_keywords_regex(FUNDING_KEYWORDS)
  
    client = cloudscraper.create_scraper()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        allowed_months = {now.month, (now - datetime.timedelta(days=30)).month} 
        
        logger.info(f"Scraping sitemap: {URL[0]}")
        sitemap_response = await fetch_with_cloudscraper(client, URL[0])
        sitemap_root = etree.fromstring(sitemap_response.content)

        namespaces = {"sitemap_ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for sitemap_node in sitemap_root.findall(".//sitemap_ns:sitemap", namespaces):
            loc_el = sitemap_node.find("sitemap_ns:loc", namespaces)
            lastmod_el = sitemap_node.find("sitemap_ns:lastmod", namespaces)
            if loc_el is not None and loc_el.text and "post-sitemap" in loc_el.text: # filter 1
                # Apply date filter to the sitemap itself
                if lastmod_el is not None and lastmod_el.text:
                    try:
                        sitemap_mod_date = dateparser.parse(lastmod_el.text.strip()).astimezone(datetime.timezone.utc) #filter 2
                        if sitemap_mod_date.year == now.year and sitemap_mod_date.month in allowed_months:
                            child_sitemap_urls.append(loc_el.text)
                    except (ValueError, TypeError, AttributeError):
                        continue # Ignore if date parsing for the sitemap fails
        logger.info(f"Found {len(child_sitemap_urls)} relevant child sitemaps to process.")

        child_sitemap_tasks = [fetch_with_cloudscraper(client, url) for url in child_sitemap_urls]
        child_sitemap_responses = await asyncio.gather(*child_sitemap_tasks)

        final_article_urls = [] # This will store ONLY the final article URLs

        for response in child_sitemap_responses:
            try:
                root = etree.fromstring(response.content)
            except etree.XMLSyntaxError as e:
                logger.error(f"Failed to parse child sitemap {response.url}: {e}")
                continue
            for url_node in root.findall(".//sitemap_ns:url", namespaces):
                loc_el = url_node.find("sitemap_ns:loc", namespaces)
                lastmod_el = url_node.find("sitemap_ns:lastmod", namespaces)

                if loc_el is not None and loc_el.text and lastmod_el is not None and lastmod_el.text:
                    try:
                        article_pub_date = datetime.datetime.fromisoformat(lastmod_el.text.replace('Z', '+00:00'))
                        if article_pub_date.year == now.year and article_pub_date.month in allowed_months:
                            url_link = loc_el.text
                            # Apply keyword filter to the article URL
                            if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link):
                                final_article_urls.append(url_link)
                    except (ValueError, TypeError, AttributeError):
                        continue # Ignore if date parsing for the article fails
        logger.info(f"Found {len(final_article_urls)} articles matching all filters.")
        tasks = [extract_paragraphs(client, url) for url in final_article_urls]
        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine
            if paragraphs:
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

        logger.info("Done fetching data from eu_entrepreneur")
        return results
    except Exception as e:
        logger.exception(f"An error occurred during the eu_entrepreneur fetching process: {str(e)}")

        return {"urls": [], "paragraphs": []}
    finally:
        client.close()

async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await fetch_with_cloudscraper(client, url)

        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//div[contains(@class, 'gate-check piano-check')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main() -> Dict[str, Any]:
    start_time = time.perf_counter()
    async with limiter:
        links_and_paragraphs = await fetch_eu_entrepreneur_data()

        if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
            try:
                result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
            except Exception as e:
                logger.error(f"Failed to extract AI content from eu_entrepreneur's data: {str(e)}")
                result = {}
        else:
            logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")
            result = {}

        llm_results = copy.deepcopy(funding_data_dict)
        if result:
            for key, value_list in result.items():
                if key in llm_results and isinstance(value_list, list):
                    llm_results[key].extend(value_list)
                elif key in llm_results:
                    llm_results[key] = value_list

            llm_results["source"].append("eu entrepreneur")
            urls = links_and_paragraphs.get("urls")
            llm_results["link"] = urls

        else:
            logger.warning("AI extraction for eu_entrepreneur returned no data. No logging will happen")

        duration = time.perf_counter() - start_time
        logger.info(f"eu_entrepreneur took {duration:.2f} seconds")

        return llm_results

if __name__ == "__main__":
    asyncio.run(main())