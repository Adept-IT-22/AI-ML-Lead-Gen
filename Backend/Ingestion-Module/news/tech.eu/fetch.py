# This file fetches information from tech.eu/sitemap/news.xml

#========IMPORTS==========
import re
import time
import json
import httpx
import aiofiles
import asyncio
import logging
from lxml import etree

#logger = logging.getLogger()

#============URLs===============
URL = "https://tech.eu/sitemap/news.xml"

async def fetch_tech_eu_data()->dict:

    #=======DATA STRUCTURE========
    data = {
        "type": "news",
        "article_title": [],
        "article_link": [],
        "article_date": [],
        "article_time": [],
        "company_name": [],
        "amount_raised": [],
        "currency": [],
        "keywords": []
    }
    
    #=======FETCH DATA==========
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(URL, timeout=5.0)
            if response.status_code != 200:
                logging.error(f"Failed to fetch URL: {URL} - Status code: {response.status_code}")
                return {}

            root = etree.fromstring(response.content) #type: ignore

            #=========NAMESPACES=============
            namespaces = {
                "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "n" : "http://www.google.com/schemas/sitemap-news/0.9"
            }
                
            #==========MULTIPLIERS===========
            multipliers = {
                "K": 1_000, 
                "M": 1_000_000, 
                "B":1_000_000_000
                }

            #===========PARSE THE DATA================
            for url in root.findall('ns:url', namespaces):
                article_link = url.find('ns:loc', namespaces).text
                unclean_article_date = url.find('n:news/n:publication_date', namespaces).text
                article_date = unclean_article_date.split("T")[0]
                article_time = unclean_article_date.split("T")[1]
                article_title = url.find('n:news/n:title', namespaces).text
                article_keywords = [url.find('n:news/n:keywords', namespaces).text]
                company_name = article_keywords[0].split(",")[0] if "," in article_keywords else article_keywords
                
                #Regex for amount and currency
                pattern = r'([€#$])([\d,\.]+)([MBK]?)'
                match = re.search(pattern, article_title)
                
                if match:
                    currency = match.group(1)
                    amount = float(match.group(2).replace(",", ""))
                    multiplier = match.group(3)
                else:
                    currency = 'N/A'
                    amount = 0
                    multiplier = ''
                
                amount_raised = amount * multipliers.get(multiplier, 1)
                
                #=========APPEND TO DICTIONARY==========
                data["article_title"].append(article_title)
                data["article_link"].append(article_link)
                data["article_date"].append(article_date)
                data["article_time"].append(article_time)
                data["company_name"].append(company_name)
                data["amount_raised"].append(amount_raised)
                data["currency"].append(currency)
                data["keywords"].append(article_keywords)

            #======================WRITE TO FILE====================
            async with aiofiles.open("results.txt", "a") as file:
                await file.write("==============NEW DATA==================\n")
                await file.writelines(json.dumps(data, indent=2))

        except Exception as e:
            logging.exception(f"Error fetching/parsing {URL}: {str(e)}")
    
    return data
    
if __name__ == "__main__":
    start_time = time.perf_counter()
    result = asyncio.run(fetch_tech_eu_data())
    print(json.dumps(result, indent=2))
    duration = time.perf_counter() - start_time
    print(f"This task took {duration} seconds")