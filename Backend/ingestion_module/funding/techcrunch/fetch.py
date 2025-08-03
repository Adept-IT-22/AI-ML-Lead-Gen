#This file handles fetching of techcrunch funding news and feeding it to an llm

import copy
import time
import json
import httpx
import logging
import asyncio
import aiofiles
from lxml import etree, html
from typing import List, Dict, Any
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction

logger = logging.getLogger()

#==============URL==============
URL = "https://techcrunch.com/news-sitemap.xml"

"""
This code will work by traversing Techcrunch's sitemap, extracting the URLs
that are AI funding related, opening them and fetching their paragraphs then
feeding those paragraphs to the LLM for it to extract meaningful information
"""

#============TRAVERSE SITEMAP================
async def traverse_sitemap(client:httpx.AsyncClient, url: str)->Dict[str, List[Any]]:
    logger.info(f"Sitemap traversal for {url} starting....")
    try:
        #Fetch w/error handling
        response = await client.get(url)
        response.raise_for_status()

        #Parse XML
        root = etree.fromstring(response.content)

        #Namespaces
        namespaces = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9"
        }


        article_data = {
            "article_link": [],
            "article_title": [],
            "article_date": []
        }

        for url in root.findall('ns:url', namespaces):
            article_link = url.find('ns:loc', namespaces).text

            if article_link is not None and ("ai-" in article_link and "raise" in article_link):
                article_data["article_link"].append(article_link)

                article_date_and_time = url.find('news:news/news:publication_date', namespaces).text
                article_date = article_date_and_time.split("T")[0] if article_date_and_time is not None else None
                article_data["article_date"].append(article_date if article_date is not None else "")

                article_title = url.find('news:news/news:title', namespaces).text
                article_data["article_title"].append(article_title if article_title is not None else "")

        logger.info("Sitemap traversal done")
        return article_data
    except Exception as e:
        logger.error(f"Error traversing sitemap: {str(e)}")
        return {
            "article_link": [],
            "article_title": [],
            "article_date": []
        }


async def get_paragraphs(client: httpx.AsyncClient, urls: List[str])->Dict[str, List[Any]]:
    logger.info("Getting paragraphs from urls...")

    url_paragraph_dict = {"urls": [], "paragraphs": []}

    if not urls:
        logger.error("Urls not found")
        return url_paragraph_dict

    try:
        tasks = [extract_paragraph(client, url) for url in urls]

        async for task in asyncio.as_completed(tasks):
            url, paragraphs = await task
            url_paragraph_dict["urls"].append(url if url is not None else "")
            url_paragraph_dict["paragraphs"].append('\n'.join(paragraphs) if paragraphs is not None else "")

        logger.info("Done getting paragraphs from urls")
        return url_paragraph_dict

    except Exception as e:
        logger.error(f"Failed getting paragraphs from url: {str(e)}")
        return {"urls": [], "paragraphs": []}

async def extract_paragraph(client: httpx.AsyncClient, url: str)->tuple[str, List[Any]]:
    logger.info(f"Fetching paragraphs from {url}")

    try:
        #Make request to url
        response = await client.get(url)
        response.raise_for_status()

        #Create an element tree
        root = html.fromstring(response.text)

        paragraph_nodes = root.xpath("//p[contains(@class, 'wp-block-paragraph')]")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logger.info(f"Fetching paragraphs from {url} done")
        return url, paragraphs

    except Exception as e:
        logger.error(f"Failed fetching paragraph from {url}: {str(e)}")
        return url, []

async def main():
    start_time = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        #Get article title, link and date
        article_data = await traverse_sitemap(client, URL)
        article_links = [link for link in article_data["article_link"] if link is not None]

        #Fetch the necessary paragraphs for each url
        links_and_paragraphs = await get_paragraphs(client, article_links)

        #Feed those to the LLM
        try:
            extracted_data = await finalize_ai_extraction(links_and_paragraphs)
        except Exception as e:
            logger.error(f"Failed to extract AI content from TechCrunch's data: {str(e)}")
            extracted_data = {}

        if extracted_data:
            llm_results =  copy.deepcopy(funding_data_dict)

            #Add data to llm_results
            for key, value_list in extracted_data.items():
                if key in llm_results and isinstance(llm_results[key], List):
                    llm_results[key].extend(value_list)
                elif key in llm_results:
                    llm_results[key] = value_list

            #Add results to file
            logger.info("Adding llm results to file...")
            async with aiofiles.open("techcrunch_data.txt", "a") as file:
                await file.writelines(json.dumps(llm_results, indent=2))
            logger.info("Done writing llm_results to file")
        else:
            logger.warning("AI extraction for TechCrunch returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"This file ran for {duration:.2f} seconds")

asyncio.run(main())