import copy
import time
import json
import httpx
import re
import asyncio
import logging
import datetime
from lxml import etree, html
from lxml.etree import XMLSyntaxError
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO) # TEST WITH AND WITHOUT 

#============URLs==============
URL = ["https://www.reuters.com/arc/outboundfeeds/news-sitemap/?outputType=xml"]

#============KEYWORDS===============
FUNDING_KEYWORDS = ["funding", "raises", "closes", "nets", "secures", "awarded", "notches", "lands"] 
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning"]

# Compile regex patterns for more precise keyword matching
def compile_keywords_regex(keywords):
    # Escape special regex characters and replace spaces with [ -] for URL matching
    patterns = []
    for keyword in keywords:
        escaped_keyword = re.escape(keyword)
        # Allow spaces or hyphens in multi-word keywords in URLs
        pattern = r'\b' + escaped_keyword.replace(r'\ ', r'[ -]') + r'\b'
        patterns.append(pattern)
    return re.compile('|'.join(patterns), re.IGNORECASE)


async def fetch_with_retries(client: httpx.AsyncClient, url: str, retries: int = 3, delay: int = 5):
    """Fetch a URL with retries and delay for rate-limiting."""
    for attempt in range(retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning(f"Rate limited. Retrying {url} in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception(f"Failed to fetch {url} after {retries} retries")

async def fetch_reuters_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from reuters...")

    #=========NAMESPACES=============
    namespaces = {
        "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "n": "http://www.google.com/schemas/sitemap-news/0.9"
    }

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
            #================fetch both top-level sitemaps concurrently===============
            top_level_tasks = [fetch_with_retries(client, url) for url in URL]
            top_level_responses = await asyncio.gather(*top_level_tasks)

            now = datetime.datetime.now(datetime.timezone.utc)
            allowed_months = {now.month, (now - datetime.timedelta(days=30)).month}

            for response in top_level_responses:
                try:
                    root = etree.fromstring(response.content)
                    # Directly process article links from the fetched sitemap
                    for url_node in root.findall(".//ns:url", namespaces):
                        loc_el = url_node.find("ns:loc", namespaces)
                        # Explicitly check for date tags to avoid truth-testing ambiguity
                        lastmod_el = url_node.find("n:publication_date", namespaces)
                        if lastmod_el is None:
                            lastmod_el = url_node.find("ns:lastmod", namespaces)
                        
                        if loc_el is not None and loc_el.text and lastmod_el is not None and lastmod_el.text:
                            try:
                                # handle both aware and naive datetimes**************
                                pub_date_str = lastmod_el.text.replace('Z', '+00:00')
                                pub_date = datetime.datetime.fromisoformat(pub_date_str)
                                if pub_date.tzinfo is not None:
                                    pub_date = pub_date.astimezone(datetime.timezone.utc)
                                
                                # Apply date filter, then keyword filter
                                if pub_date.year == now.year and pub_date.month in allowed_months:
                                    url_link = loc_el.text
                                     # Use regex for more precise keyword matching
                                    if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link): 
                                        article_links.append(url_link)
                            except (ValueError, TypeError):
                                continue
                except XMLSyntaxError as e:
                    logger.error(f"Failed to parse sitemap XML from {response.url}: {str(e)}")
                    continue

            # extract paragraphs from article links
            tasks = [extract_paragraphs(client, url) for url in article_links]
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

            logger.info("Done fetching data from reuters")
            return results

        except Exception as e:
            logger.exception(f"Error fetching/parsing reuters sitemaps: {str(e)}")

    return {"urls": [], "paragraphs": []}


async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)
        paragraphs = []
        
        # Loop through possible paragraph indices until we don't find any more
        index = 1
        while True:
            paragraph_nodes = root.xpath(f"//div[@data-testid='paragraph-{index}']//p")
            if not paragraph_nodes:  # No more paragraphs found
                break
                
            # Add the found paragraph text
            for node in paragraph_nodes:
                text = node.text_content().strip()
                if text:
                    paragraphs.append(text)
            index += 1

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_reuters_data()

    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
        except Exception as e:
            logger.error(f"Failed to extract AI content from reuters beat's data: {str(e)}")
            result = {}
    else:
        logger.error("No links or paragraphs found for AI extraction. Skipping LLM call")
        result = {}

    llm_results = None
    if result:
        llm_results = copy.deepcopy(funding_data_dict)

        for key, value_list in result.items():
            if key in llm_results and isinstance(value_list, list):
                llm_results[key].extend(value_list)
            elif key in llm_results:
                llm_results[key] = value_list

        llm_results["source"].append("reuters.com")
        urls = links_and_paragraphs.get("urls")
        llm_results["link"] = urls

    else:
        logger.warning("AI extraction for reuters returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"reuters took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())