import copy
import time
import json
import re
import asyncio
import logging
import datetime
import cloudscraper
import dateparser
from lxml import etree, html
from aiolimiter import AsyncLimiter
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

limiter = AsyncLimiter(max_rate=5, time_period=1)

#============URLs==============
URL = "https://vcnewsdaily.com/"

#============KEYWORDS===============
FUNDING_KEYWORDS = ["funding", "raises", "closes", "nets", "secures", "awarded", "notches", "lands", "seed", "pre-seed", "series"] 
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning", "ai-powered"]

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

async def fetch_vc_news_daily_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from VC News Daily...")

    results = {"urls": [], "paragraphs": []}
    final_article_urls = []

    AI_KEYWORDS_REGEX = compile_keywords_regex(AI_KEYWORDS)
    FUNDING_KEYWORDS_REGEX = compile_keywords_regex(FUNDING_KEYWORDS)
  
    client = cloudscraper.create_scraper()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        allowed_months = {now.month, (now - datetime.timedelta(days=30)).month}
        
        logger.info(f"Scraping main page: {URL}")
        main_page_response = await fetch_with_cloudscraper(client, URL)
        main_page_root = html.fromstring(main_page_response.text)

        article_containers = main_page_root.xpath("//div[contains(@class, 'col-md-6') and contains(@class, 'mb-4')]")

        for article_node in article_containers:
            link_node = article_node.find(".//a")
            
            date_nodes = article_node.xpath(".//small[contains(@class, 'posted-date')]")
            description_nodes = article_node.xpath(".//p[contains(@class, 'article-paragraph')]")
            date_node = date_nodes[0] if date_nodes else None
            description_node = description_nodes[0] if description_nodes else None
            
            if link_node is None or date_node is None or description_node is None:
                continue

            url = link_node.get("href")
            date_str = date_node.text_content().strip()
            description = description_node.text_content().strip()

            if not all([url, date_str, description]):
                continue

            pub_date = dateparser.parse(date_str).replace(tzinfo=datetime.timezone.utc)
            if pub_date.year == now.year and pub_date.month in allowed_months:
                if FUNDING_KEYWORDS_REGEX.search(description) and AI_KEYWORDS_REGEX.search(description):
                    final_article_urls.append(url)

        logger.info(f"Found {len(final_article_urls)} articles matching all filters.")

        # Extract paragraphs from the final list of article links
        tasks = [extract_paragraphs(client, url) for url in final_article_urls]
        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine
            if paragraphs:
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

        logger.info("Done fetching data from VC News Daily")
        return results

    except Exception as e:
        logger.exception(f"An error occurred during the VC News Daily fetching process: {str(e)}")
        return {"urls": [], "paragraphs": []}
    finally:
        client.close()


async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await fetch_with_cloudscraper(client, url)
        root = html.fromstring(response.text)
        # This selector targets the main content area on the article page
        paragraph_nodes = root.xpath("//div[contains(@id, 'fullArticle')]")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]
        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs
    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")
    return url, []

async def main():
    start_time = time.perf_counter()
    async with limiter:
        links_and_paragraphs = await fetch_vc_news_daily_data()

        if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
            try:
                result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
            except Exception as e:
                logger.error(f"Failed to extract AI content from VC News Daily's data: {str(e)}")
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

            llm_results["source"].append("VC News Daily")
            urls = links_and_paragraphs.get("urls")
            llm_results["link"] = urls

        else:
            logger.warning("AI extraction for VC News Daily returned no data. No logging will happen")

        duration = time.perf_counter() - start_time
        logger.info(f"VC News Daily took {duration:.2f} seconds")

        return llm_results

if __name__ == "__main__":
    asyncio.run(main())