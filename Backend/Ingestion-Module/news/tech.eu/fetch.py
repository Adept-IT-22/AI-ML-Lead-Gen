# This file fetches information from tech.eu/sitemap/news.xml

#========IMPORTS==========
import re
import requests
import logging
from lxml import etree
from bs4 import BeautifulSoup

logger = logging.getLogger()

#=======DATA STRUCTURE========
data = {
    "article_title": [],
    "article_link": [],
    "article_date": [],
    "article_time": [],
    "company_name": [],
    "amount_raised": [],
    "currency": [],
    "keywords": []
}

def fetch_tech_eu_data()->dict:

    #=======FETCH AND PARSE==========
    URL = "https://tech.eu/sitemap/news.xml"
    response = requests.get(URL)
    if(response.status_code != 200):
       logger.error("Couldn't fetch data")
       raise Exception(f"Couldn't fetch data. {response.status_code}")
       return

    root = etree.fromstring(response.content)

    #=========NAMESPACES=============
    namespaces = {
        "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "n" : "http://www.google.com/schemas/sitemap-news/0.9"
    }
        
    #==========MULTIPLIERS===========
    multipliers = {"K": 1_000, "M": 1_000_000, "B":1_000_000_000}

    #==========LINKS==============
    #Add to file
    with open("results.txt", "a") as file:
        for url in root.findall('ns:url', namespaces):
            article_link = url.find('ns:loc', namespaces).text
            unclean_article_date = url.find('n:news/n:publication_date', namespaces).text
            article_date = unclean_article_date.split("T")[0]
            article_time = unclean_article_date.split("T")[1]
            article_title = url.find('n:news/n:title', namespaces).text
            article_keywords = [url.find('n:news/n:keywords', namespaces).text]
            company_name = article_keywords[0].split(",")[0]
            
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
            
            amount_currency = currency
            amount_raised = amount * multipliers.get(multiplier, 1)

        
            file.write("==============NEW DATA==================\n")
            file.writelines([f"Title: {article_title}\n",
                            f"Link: {article_link}\n", 
                            f"Date: {article_date}\n", 
                            f"Time: {article_time}"
                            f"Company Name: {company_name}\n", 
                            f"Amount Raised: {amount_raised}\n", 
                            f"Currency: {amount_currency}\n", 
                            f"Keywords {article_keywords}\n",
                            "\n"
                            ])

            #Append to dictionary
            data["article_title"].append(article_title)
            data["article_link"].append(article_link)
            data["article_date"].append(article_date)
            data["article_time"].append(article_time)
            data["company_name"].append(company_name)
            data["amount_raised"].append(amount_raised)
            data["currency"].append(currency)
            data["keywords"].append(article_keywords)

    print(data)
    return data
    
if __name__ == "__main__":
    fetch_tech_eu_data()