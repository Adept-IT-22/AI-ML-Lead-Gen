# This file fetches information from tech.eu/sitemap/news.xml

#========IMPORTS==========
import re
import requests
from lxml import etree
from bs4 import BeautifulSoup


#=======FETCH AND PARSE==========
URL = "https://tech.eu/sitemap/news.xml"
response = requests.get(URL)
root = etree.fromstring(response.content)

#=========NAMESPACES=============
namespaces = {
    "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "n" : "http://www.google.com/schemas/sitemap-news/0.9"
}
    
#==========MULTIPLIERS===========
multipliers = {"K": 1_000, "M": 1_000_000, "B":1_000_000_000}

#==========LINKS==============
for url in root.findall('ns:url', namespaces):
    article_link = url.find('ns:loc', namespaces).text
    article_date = url.find('n:news/n:publication_date', namespaces).text
    article_title = url.find('n:news/n:title', namespaces).text
    article_keywords = [url.find('n:news/n:keywords', namespaces).text]
    company_name = article_keywords[0].split(",")[0]
    
    #Regex for amount and currency
    pattern = r'([€#$])([\d\.]+)([MBK])'
    match = re.search(pattern, article_title)
    

    if match:
        currency = match.group(1)
        amount = float(match.group(2))
        multiplier = match.group(3)
    else:
        currency = 'N/A'
        amount = 0
        multiplier = ''
    
    amount_currency = currency
    amount_raised = amount * multipliers.get(multiplier, 1)


    with open("results.txt", "a") as file:
        file.write("==============NEW DATA==================\n")
        file.writelines([f"Title: {article_title}\n",
                         f"Link: {article_link}\n", 
                         f"Date: {article_date}\n", 
                         f"Company Name: {company_name}\n", 
                         f"Amount Raised: {amount_raised}\n", 
                         f"Currency: {amount_currency}\n", 
                         f"Keywords {article_keywords}\n",
                         "\n"
                         ])

        print(f"Link: {article_link}\n")
        print(f"Date: {article_date}\n")
        print(f"Title: {article_title}")
        print(f"Keywords: {article_keywords}\n")
        print(f"Company Name: {company_name}\n")
        print(f"Currency: {amount_currency}\n")
        print(f"Amount Raised: {int(amount_raised):,}\n")
