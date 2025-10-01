import re
import copy
import json
import time
import httpx
import asyncio
import logging
import aiofiles
import cloudscraper
from lxml import etree, html
from typing import Dict, List
from services.request_headers import get_header
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_fetched_data

logger = logging.getLogger()

#Configure semaphore
MAX_CONNECTIONS = 10


"""
This website's sitemap is a list of nested sitemaps.
We therefore have to parse them until we find the latest one.
Once we find the latest one, we must open it and parse all the
urls inside it searching for ai-related urls. We then open those
urls and fetch all important data-filled paragraphs. That's what
we eventually return: each url and its paragraphs.
"""
#===============PARENT SITEMAP================
URL = "https://www.finsmes.com/wp-sitemap.xml"

#=================NAMESPACE====================
namespace = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"
    }

#==============FIND NEWEST SITEMAP=============
"""
Since the sitemaps are organized from 1 to the latest, we only
need the latest one. The method below finds the latest sidemap.
"""
async def fetch_sync(client: cloudscraper.CloudScraper, url: str):
    """Run blocking cloudscraper.get in a thread."""
    return await asyncio.to_thread(client.get, url)

async def find_newest_sitemap(client: cloudscraper.CloudScraper, url: str)->str:
    logger.info("Fetching latest sitemap...")

    #Regex to search for posts only
    pattern = re.compile(r'-post-(\d+)\.xml')
    
    try:
        #Fetching 
        response = await fetch_sync(client, url)
        response.raise_for_status()

        #Parse XML
        root = etree.fromstring(response.content) #type: ignore

        #Sitemap URLs
        sitemap_urls = root.xpath("//sitemap:loc/text()", namespaces=namespace)

        #Return the latest url
        highest_number = -1
        latest_sitemap = ""

        for url in sitemap_urls:
            if(match := pattern.search(url)):
                current_number = int(match.group(1))
                if current_number > highest_number:
                    highest_number = current_number
                    latest_sitemap = url

        logger.info(f"Latest sitemap: {latest_sitemap}")
        logger.info("Fetching latest sitemap done")
        return latest_sitemap

    except Exception as e:
        logger.error(f"Error fetching/parsing {url}: {str(e)}")
        return

#Extract all ai funding article links from the latest sitemap
async def fetch_ai_funding_article_links(client: cloudscraper.CloudScraper, url: str)->list:
    logger.info(f"Fetching AI specific urls...")
    try:
        #=======FETCH DATA==========
        response = await fetch_sync(client, url)
        response.raise_for_status()

        root = etree.fromstring(response.content) #type: ignore         

        #===========PARSE THE DATA================
        ai_funding_articles = []
        urls = root.findall("sitemap:url", namespace)
        for url in urls:
            article_link = url.find("sitemap:loc", namespace).text
            if "-ai-" in article_link and ("funding" in article_link or "raises" in article_link or "-closes" in article_link or "-nets" in article_link or "-secures" in article_link):
                ai_funding_articles.append(article_link)

        logger.info("Feching AI specific urls done")
        return list(set(ai_funding_articles))

    except Exception as e:
        logger.error(f"Error fetching/parsing {URL}: {str(e)}")
        return []

"""
Now we open the links and extract the necessary paragraphs before feeding it to the LLM
"""
async def get_paragraphs(client: cloudscraper.CloudScraper, urls: list, semaphore) -> Dict[str, List[str]]:
    logger.info("Getting paragraphs from urls...")
    if not urls:
        logger.error("List of AI specific Urls Not Found")
        return {"urls": [], "paragraphs": []}
    
    try:
        results = {"urls": [], "paragraphs": []}
        tasks = [extract_paragraphs(client, url, semaphore) for url in urls]                
        
        """
        Coroutine below is an awaitable and not the actual coroutine
        which is why we have to await it
        """

        for coroutine in asyncio.as_completed(tasks):
            url, paragraphs = await coroutine 
            results["urls"].append(url)
            results["paragraphs"].append('\n'.join(paragraphs))

        logger.info("Done getting paragraphs from urls")
        return results

    except Exception as e:
        logger.error("Failed getting paragraphs from urls")
    
    return {"": [""]}
            
#Function that does the actual extraction
async def extract_paragraphs(client: cloudscraper.CloudScraper, url: str, semaphore)->tuple[str, list[str]]:
    async with semaphore:
        logger.info(f"Fetching paragraphs from {url}...")
        try:
            response = await fetch_sync(client, url)
            response.raise_for_status()

            root = html.fromstring(response.text)

            #Extract paragraphs from the class below
            paragraph_nodes = root.xpath("//div[contains(@class, 'tdb-block-inner') and contains(@class, 'td-fix-index')]//p")
            paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

            logger.info(f"Done fetching paragraphs")
            return url, paragraphs

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch paragraphs from {url}")
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            
        return url, []


async def main()->Dict[str, List[str]]: #Allows us to run the code asynchronously to avoid blocking
    logger.info("Fetching from FinSMEs...")
    semaphore = asyncio.Semaphore(MAX_CONNECTIONS)
    current_time = time.perf_counter()

    client = cloudscraper.create_scraper()
    newest_sitemap = await find_newest_sitemap(client, URL)
    if newest_sitemap:
        ai_urls = await fetch_ai_funding_article_links(client, newest_sitemap)
        if ai_urls:
            results = await get_paragraphs(client, ai_urls, semaphore)

    #Check if results has urls in the first place
    if results["urls"]:

        #Feed the results to the llm
        try:
            extracted_data = await finalize_ai_extraction(results)
        except Exception as e:
            logger.error(f"Failed to extract AI content from FinSMEs data: {str(e)}")
            extracted_data = {}

        if extracted_data:
            llm_results = copy.deepcopy(funding_fetched_data)

            #Append extracted_data to llm_results
            for key, value_list in extracted_data.items():
                if key in llm_results and isinstance(llm_results[key], list) and isinstance(value_list, list):
                    llm_results[key].extend(value_list)
                elif key in llm_results:
                    llm_results[key] = value_list

            llm_results["source"] = "FinSMEs"
            llm_results["link"].extend(results["urls"])

        else:
            logger.warning("AI extraction for FinSMEs returned no data. No logging will happen")

        duration = time.perf_counter() - current_time
        logger.info(f"Program ran for {duration:.2f} seconds")
    
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())