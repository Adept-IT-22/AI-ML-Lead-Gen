import re
import json
import time
import httpx
import asyncio
import logging
from lxml import etree, html
from typing import Dict, List

#====================FIND URL====================
"""
This website's sitemap is a list of numbered sitemaps.
We therefore have to parse them until we find the latest one.
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
async def find_newest_sitemap(url: str)->str:
    logging.info("Fetching latest sitemap...")

    #Regex to search for posts only
    pattern = re.compile(r'-post-(\d+)\.xml')
    
    async with httpx.AsyncClient() as client:
        try:
            #Fetching w/error handling
            response = await client.get(url)
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

            print(f"Latest sitemap: {latest_sitemap}")
            logging.info("Fetching latest sitemap done")
            return latest_sitemap

        except Exception as e:
            logging.error(f"Error fetching/parsing {url}: {str(e)}")
            return

#Extract all ai funding article links from the latest sitemap
async def fetch_ai_funding_article_links(url: str)->list:
    logging.info(f"Fetching AI specific urls...")
    try:
        #=======FETCH DATA==========
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

        root = etree.fromstring(response.content) #type: ignore         

        #===========PARSE THE DATA================
        ai_funding_articles = []
        urls = root.findall("sitemap:url", namespace)
        for url in urls:
            article_link = url.find("sitemap:loc", namespace).text
            if "-ai-" in article_link and ("funding" in article_link or "raises" in article_link):
                ai_funding_articles.append(article_link)

        print(json.dumps(ai_funding_articles, indent=2))
        logging.info("Feching AI specific urls done")
        return list(set(ai_funding_articles))

    except Exception as e:
        logging.error(f"Error fetching/parsing {URL}: {str(e)}")

"""
Now we open the links and extract the necessary paragraphs before feeding it to the LLM
"""
async def get_paragraphs(urls: list) -> Dict[str, List[str]]:
    logging.info("Getting paragraphs from urls...")
    if not urls:
        logging.error("List of AI specific Urls Not Found")
        return {"urls": [], "paragraphs": []}
    
    try:
        results = {"urls": [], "paragraphs": []}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = [extract_paragraphs(client, url) for url in urls]                
            
            """
            Coroutine below is an awaitable and not the actual coroutine
            which is why we have to await it
            """

            for coroutine in asyncio.as_completed(tasks):
                url, paragraphs = await coroutine 
                results["urls"].append(url)
                results["paragraphs"].append(paragraphs)

        logging.info("Done getting paragraphs from urls")
        return results

    except Exception as e:
        logging.error("Failed getting paragraphs from urls")
    
    return {"": [""]}
            
#Function that does the actual extraction
async def extract_paragraphs(client: httpx.AsyncClient, url: str)->tuple[str, list[str]]:
    logging.info(f"Fetching paragraphs from {url}...")
    try:
        response = await client.get(url)
        response.raise_for_status()

        root = html.fromstring(response.text)

        #Extract paragraphs from the class below
        paragraph_nodes = root.xpath("//div[contains(@class, 'tdb-block-inner') and contains(@class, 'td-fix-index')]//p")
        paragraphs = [node.text_content().strip() for node in paragraph_nodes if node.text_content().strip()]

        logging.info(f"Done fetching paragraphs")
        return url, paragraphs

    except httpx.HTTPStatusError as e:
        logging.error(f"Failed to fetch paragraphs from {url}")
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        
    return url, []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    async def main(): #Allows us to run the code asynchronously to avoid blocking
        logging.info("Fetching from FinSMEs...")
        current_time = time.perf_counter()
        newest_sitemap = await find_newest_sitemap(URL)
        if newest_sitemap:
            ai_urls = await fetch_ai_funding_article_links(newest_sitemap)
            if ai_urls:
                results = await get_paragraphs(ai_urls)
                print(json.dumps(results, indent=2))
        logging.info("Done fetching from FinSMEs.Time for AI information extraction")
        running_time = time.perf_counter() - current_time
        print(f"Program ran for {running_time}")
    
    asyncio.run(main())