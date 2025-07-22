from lxml import etree
import httpx
import asyncio
import logging

import lxml.etree
from utils.data_structures.news_data_structure import fetched_data

URL = "https://www.finsmes.com/wp-sitemap-posts-post-45.xml"

async def fetch_finsmes_links(url: str)->dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if(response.status_code != 200):
            logging.error("Couldn't fetch data")
            raise Exception(f"Couldn't fetch data. {response.status_code}")

    root = etree.fromstring(response.content) #type: ignore 


    return fetched_data
    




