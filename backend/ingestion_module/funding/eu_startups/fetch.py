import copy
import time
import json
import httpx
import re
import asyncio
import logging
import datetime
import dateparser
from lxml import etree, html
from lxml.etree import XMLSyntaxError
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

#============URLs==============
URL = ["https://www.eu-startups.com/sitemap_index.xml"]

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

async def fetch_eu_startups_data() -> Dict[str, List[str]]:
    logger.info("Fetching data from eu_startups...")

    namespaces = {
        "sitemap_ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "n": "http://www.google.com/schemas/sitemap-news/0.9"
    }
    
    results: Dict[str, List[str]] = {"urls": [], "paragraphs": []}
    final_links: dict[str, datetime.datetime] = {}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    AI_KEYWORDS_REGEX = compile_keywords_regex(AI_KEYWORDS)
    FUNDING_KEYWORDS_REGEX = compile_keywords_regex(FUNDING_KEYWORDS)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        try:
            # Step 1: Fetch the main sitemap index
            index_response = await fetch_with_retries(client, URL[0])
            index_root = etree.fromstring(index_response.content)

            now = datetime.datetime.now(datetime.timezone.utc)
            allowed_months = {now.month, (now - datetime.timedelta(days=30)).month}
            
            # Filter the child sitemaps from the index
            child_sitemaps_to_fetch = []
            for sitemap_node in index_root.findall(".//sitemap_ns:sitemap", namespaces):
                loc_el = sitemap_node.find("sitemap_ns:loc", namespaces)
                lastmod_el = sitemap_node.find("sitemap_ns:lastmod", namespaces)

                if loc_el is not None and loc_el.text and "post-sitemap" in loc_el.text: # filter 1 
                    # Apply date filter to the sitemap itself
                    if lastmod_el is not None and lastmod_el.text:
                        try:
                            sitemap_mod_date = dateparser.parse(lastmod_el.text.strip()).astimezone(datetime.timezone.utc) #filter 2
                            if sitemap_mod_date.year == now.year and sitemap_mod_date.month in allowed_months:
                                child_sitemaps_to_fetch.append(loc_el.text)
                        except (ValueError, TypeError, AttributeError):
                            continue # Ignore if date parsing for the sitemap fails

            logger.info(f"Found {len(child_sitemaps_to_fetch)} relevant child sitemaps to process.")

            # Process the filtered child sitemaps for articles
            child_sitemap_tasks = [fetch_with_retries(client, url) for url in child_sitemaps_to_fetch]
            child_sitemap_responses = await asyncio.gather(*child_sitemap_tasks)

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
                            # Apply date filter to the article
                            article_pub_date = dateparser.parse(lastmod_el.text.strip()).astimezone(datetime.timezone.utc) 
                            if article_pub_date.year == now.year and article_pub_date.month in allowed_months:
                                url_link = loc_el.text
                                # Apply keyword filter to the article URL
                                if url_link and AI_KEYWORDS_REGEX.search(url_link) and FUNDING_KEYWORDS_REGEX.search(url_link):
                                    final_links[url_link] = article_pub_date
                        except (ValueError, TypeError, AttributeError):
                            continue # Ignore if date parsing for the article fails

            logger.info(f"Found {len(final_links)} articles matching all filters.")

            # Extract paragraphs from the final list of article links
            tasks = [extract_paragraphs(client, url) for url in final_links.keys()]
            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine
                if paragraphs:
                    results["urls"].append(url)
                    results["paragraphs"].append("\n".join(paragraphs))

            logger.info("Done fetching data from eu_startups")
            return results

        except Exception as e:
            logger.exception(f"Error fetching/parsing eu_startups sitemaps: {str(e)}")

    return {"urls": [], "paragraphs": []}



async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//div[contains(@class, 'tdb-block-inner')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.exception(f"Failed to fetch paragraphs from {url}")

    return url, []

async def main() -> Dict[str, Any]:
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_eu_startups_data()

    if links_and_paragraphs and (links_and_paragraphs.get("urls") and links_and_paragraphs.get("paragraphs")):
        try:
            result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)
        except Exception as e:
            logger.error(f"Failed to extract AI content from eu_startups beat's data: {str(e)}")
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

        llm_results["source"].append("Eu Startups")
        urls = links_and_paragraphs.get("urls")
        llm_results["link"] = urls

    else:
        logger.warning("AI extraction for eu_startups returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"eu_startups took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())