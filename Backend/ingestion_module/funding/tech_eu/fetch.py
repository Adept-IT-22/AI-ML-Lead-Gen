# This file fetches information from tech.eu/sitemap/news.xml

#========IMPORTS==========
import re
import time
import json
import httpx
import aiofiles
import asyncio
import logging
from lxml import etree, html
from typing import Dict, List
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict
logger = logging.getLogger()

#============URLs===============
URL = "https://tech.eu/sitemap/news.xml"

async def fetch_tech_eu_data()->Dict[str, List[str]]:
    logger.info("Fetching data from tech.eu...")
    #=======FETCH DATA==========
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(URL)
            if response.status_code != 200:
                logger.error(f"Failed to fetch URL: {URL} - Status code: {response.status_code}")
                return {}
            root = etree.fromstring(response.content) #type: ignore

            #=========NAMESPACES=============
            namespaces = {
                "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "n" : "http://www.google.com/schemas/sitemap-news/0.9"
            }
                
            #===========PARSE THE DATA================
            for url in root.findall('ns:url', namespaces):
                article_link = url.find('ns:loc', namespaces).text

                #=======APPEND LINK IF AI RELATED============
                if ("-ai" in article_link or "ai-" in article_link) and "-raises" in article_link:
                    fetched_funding_data["article_link"].append(article_link)

            #=========OPEN LINK TO GET PARAGRAPHS============
            results = {"urls": [], "paragraphs": []}
            tasks = [extract_paragraphs(client, url) for url in fetched_funding_data["article_link"]]

            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine
                results["urls"].append(url)
                results["paragraphs"].append('\n'.join(paragraphs))

            logger.info("Done fetching data from tech.eu")
            logger.info("Results of fetch are...")
            logger.info(json.dumps(results, indent=2))
            return results

        except Exception as e:
            logger.exception(f"Error fetching/parsing {URL}: {str(e)}")
    
    return {"urls": [], "paragraphs": []}

async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, List[str]]:
    logger.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//div[contains(@class, 'single-post-content')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.error(f"Failed to fetch paragraphs from {url}")

    return url, []


async def main():
    start_time = time.perf_counter()
    links_and_paragraphs = await fetch_tech_eu_data()
    result = await finalize_ai_extraction(links_and_paragraphs=links_and_paragraphs)

    llm_results = funding_data_dict

    for key, value_list in result.items():
        if key in llm_results and isinstance(value_list, list):
            llm_results[key].extend(value_list)
        elif key in llm_results:
            llm_results[key] = value_list

    #Add llm results to file
    logger.info("Writing tech eu data to file...")
    async with aiofiles.open("tech_eu_data.txt", "a") as file:
        await file.writelines(json.dumps(llm_results, indent=2))
    logger.info("Done writing tech eu data to file")

    duration = time.perf_counter() - start_time
    logger.info(f"This task took {duration:.2f} seconds")
