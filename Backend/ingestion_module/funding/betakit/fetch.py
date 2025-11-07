import copy
import time
import re
import json
import httpx
import asyncio
import logging
import datetime
from lxml import etree, html
from lxml.etree import XMLSyntaxError
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO) 

#============URLs==============
URL = ["https://betakit.com/news-sitemap.xml"]

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

async def fetch_betakit_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from betakit...")

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

            for response in top_level_responses:
                try:
                    # Validate content type
                    content_type = response.headers.get("Content-Type", "")
                    if "xml" not in content_type:
                        logger.error(f"Invalid content type for {response.url}: {content_type}")
                        continue

                    root = etree.fromstring(response.content)

                    # Extract article links and publication dates
                    link_tags = [".//ns:loc", ".//link", ".//guid"]
                    date_tags = [
                        ".//n:publication_date",   # news sitemap
                        ".//ns:lastmod",           # standard sitemap
                        ".//ns:pubDate",           # RSS
                        ".//ns:date"               # custom feeds
                    ]

                    #link format
                    link_elements = []
                    for tag in link_tags:
                        elements = root.findall(tag, namespaces)
                        if elements:
                            link_elements = elements
                            break 
                    
                    #date format
                    date_elements = None
                    for tag in date_tags:
                        elements = root.findall(tag, namespaces)
                        if elements:
                            date_elements = elements
                            break

                    if link_elements and date_elements:
                        for link, date in zip(link_elements, date_elements):
                            if link is not None and date is not None:
                                try:
                                    pub_date = datetime.datetime.strptime(date.text[:10], "%Y-%m-%d")
                                except ValueError:
                                    continue # skip if date parsing fails

                                now = datetime.datetime.now()
                                if pub_date.year == now.year and pub_date.month in [now.month, (now - datetime.timedelta(days=30)).month]:
                                    url_link = link.text
                                    # Use regex for more precise keyword matching
                                    if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link): 
                                        article_links.append(url_link)  

                except XMLSyntaxError as e:
                    logger.error(f"Failed to parse XML from {response.url}: {str(e)}")
                    logger.debug(f"Response content: {response.text}")
                    continue

            # extract paragraphs from article links
            tasks = [extract_paragraphs(client, url) for url in article_links]
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

            logger.info("Done fetching data from betakit")
            return results

        except Exception as e:
            logger.exception(f"Error fetching/parsing betakit sitemaps: {str(e)}")

    return {"urls": [], "paragraphs": []}


async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//article[contains(@class, 'clearfix')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_betakit_data()

    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
        except Exception as e:
            logger.error(f"Failed to extract AI content from betakit beat's data: {str(e)}")
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

        llm_results["source"].append("betakit.com")
        urls = links_and_paragraphs.get("urls")
        llm_results["link"] = urls

    else:
        logger.warning("AI extraction for betakit returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"betakit took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())