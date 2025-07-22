import re
import json
import time
import httpx
import asyncio
import logging
from lxml import etree
from utils.data_structures.news_data_structure import fetched_data

#====================FIND URL====================
"""
This website's sitemap is a list of numbered sitemaps.
We therefore have to parse them until we find the latest one.
Once we find it, we store it and the next search starts from
that one.
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
    print("Finding latest sitemap")

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
            return latest_sitemap

        except Exception as e:
            logging.error(f"Error fetching/parsing {url}: {str(e)}")
            return

#Extract all ai funding article links from the latest sitemap
async def fetch_ai_funding_article_links(url: str)->dict:
    logging.info(f"The URL is {url}")
    try:
        #=======FETCH DATA==========
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if(response.status_code != 200):
                logging.error("Couldn't fetch data")
                raise Exception(f"Couldn't fetch data. {response.status_code}")

        root = etree.fromstring(response.content) #type: ignore         

        #===========PARSE THE DATA================
        ai_funding_articles = []
        urls = root.findall("sitemap:url", namespace)
        for url in urls:
            article_link = url.find("sitemap:loc", namespace).text
            if "-ai-" in article_link and ("funding" in article_link or "raises" in article_link):
                ai_funding_articles.append(article_link)

        print(json.dumps(ai_funding_articles, indent=2))
        return [set(ai_funding_articles)]

    except Exception as e:
        logging.error(f"Error fetching/parsing {URL}: {str(e)}")

if __name__ == "__main__":
    async def main(): #Allows us to run the code asynchronously to avoid blocking
        current_time = time.perf_counter()
        newest_sitemap = await find_newest_sitemap(URL)
        await fetch_ai_funding_article_links(newest_sitemap)
        running_time = time.perf_counter() - current_time
        print(f"Program ran for {running_time}")
    
    asyncio.run(main())




