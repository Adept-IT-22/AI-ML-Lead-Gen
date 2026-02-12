import copy
import time
import json
import httpx
import re
import asyncio
import logging
import datetime
from lxml import etree, html
from aiolimiter import AsyncLimiter
from lxml.etree import XMLSyntaxError
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)  

limiter = AsyncLimiter(max_rate=5, time_period=1)

#============URLs==============
URL = ["https://www.prnewswire.com/sitemap-news.xml"]

#============KEYWORDS===============
FUNDING_KEYWORDS = ["funding", "raises", "closes", "nets", "secures", "awarded", "notches", "lands"] 
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning"]

def compile_keywords_regex(keywords):
    # Escape special regex characters and replace spaces with [ -] for URL matching
    patterns = []
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)
        # Allow spaces or hyphens in multi-word keywords in URLs
        pattern = r'\b' + escaped_keyword.replace(r'\ ', r'[ -]') + r'\b'
        patterns.append(pattern)
    return re.compile('|'.join(patterns), re.IGNORECASE)


async def fetch_with_retries(client: httpx.AsyncClient, url: str, retries: int = 3, initial_delay: int = 2):
    """Fetch a URL with exponential backoff retries for rate-limiting.""" 
    for attempt in range(retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too Many Requests
                delay = initial_delay * (2 ** attempt)  # incremental delay = exponential backoff
                logger.warning(f"Rate limited. Retrying {url} in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception(f"Failed to fetch {url} after {retries} retries")

async def fetch_prnewswire_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from prnewswire...")

    #=========NAMESPACES=============
    namespaces = {
        "sitemap_ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "n": "http://www.google.com/schemas/sitemap-news/0.9"
    }

    sub_sitemap_urls = []
    results = {"urls": [], "paragraphs": []}
    article_links = []

    AI_KEYWORDS_REGEX = compile_keywords_regex(AI_KEYWORDS)
    FUNDING_KEYWORDS_REGEX = compile_keywords_regex(FUNDING_KEYWORDS)
  
    #========MIMICK BROWSER===========
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client: 
        try:
            # Step 1: Fetch the main sitemap index to get sub-sitemap URLs
            index_response = await fetch_with_retries(client, URL[0])
            index_root = etree.fromstring(index_response.content)
            
            # Extract URLs of the individual page sitemaps
            for sitemap_node in index_root.findall(".//sitemap_ns:sitemap", namespaces):
                loc_el = sitemap_node.find("sitemap_ns:loc", namespaces)
                if loc_el is not None and loc_el.text:
                    sub_sitemap_urls.append(loc_el.text)

            # Step 2: Fetch all sub-sitemaps concurrently
            sub_sitemap_tasks = [fetch_with_retries(client, url) for url in sub_sitemap_urls]
            sub_sitemap_responses = await asyncio.gather(*sub_sitemap_tasks)

            now = datetime.datetime.now(datetime.timezone.utc)
            allowed_months = {now.month, (now - datetime.timedelta(days=30)).month}

            # Step 3: Process each sub-sitemap to find article links
            for response in sub_sitemap_responses:
                try:
                    root = etree.fromstring(response.content)
                    for url_node in root.findall(".//sitemap_ns:url", namespaces):
                        loc_el = url_node.find("sitemap_ns:loc", namespaces)
                        
                        # PRNewswire uses a nested structure for news data
                        news_el = url_node.find("n:news", namespaces)
                        if news_el is None:
                            continue

                        date_el = news_el.find("n:publication_date", namespaces)

                        if loc_el is not None and loc_el.text and date_el is not None and date_el.text:
                            try:
                                # Use fromisoformat for robust date parsing with timezones
                                pub_date = datetime.datetime.fromisoformat(date_el.text)
                                
                                # Apply date filter, then keyword filter
                                if pub_date.year == now.year and pub_date.month in allowed_months:
                                    url_link = loc_el.text
                                    if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link):
                                        article_links.append(url_link)
                            except (ValueError, TypeError):
                                continue # Ignore if date parsing fails
                except XMLSyntaxError as e:
                    logger.error(f"Failed to parse XML from {response.url}: {str(e)}")
                    continue

            # Step 4: Extract paragraphs from the collected article links
            tasks = [extract_paragraphs(client, url) for url in article_links]
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

            logger.info("Done fetching data from prnewswire")
            return results

        except Exception as e:
            logger.exception(f"Error fetching/parsing prnewswire sitemaps: {str(e)}")

    return {"urls": [], "paragraphs": []}


async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)

        # Try several common PR Newswire content selectors
        paragraph_nodes = root.xpath("//div[contains(@class, 'col-lg-10')]//p | //section[contains(@class, 'release-body')]//p | //article//p")
        
        # Filter out empty or very short noise paragraphs if necessary, but here we just take non-empty ones
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_prnewswire_data()
    async with limiter:

        if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
            try:
                result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
            except Exception as e:
                logger.error(f"Failed to extract AI content from prnewswire beat's data: {str(e)}")
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

        llm_results["source"].append("prnewswire")
        urls = links_and_paragraphs.get("urls")
        llm_results["link"] = urls

    else:
        logger.warning("AI extraction for prnewswire returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"prnewswire took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
