#This file uses RSS to fetch the latest AI funding news from Google News

import copy
import time
import httpx
import logging
import asyncio
from lxml import etree, html
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from utils.data_structures.news_data_structure import fetched_funding_data as funding_data_dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

URL = "https://news.google.com/rss/search?q=ai+funding"
funding_keywords = ['raises', 'closes', 'nets', 'secures', 'awarded', 'notches', 'lands']

async def fetch_rss_feed(client, url):
    logger.info("Fetching Google News....")

    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Error fetching RSS feed: {e}")
        raise

    article_data = {
        'titles': [],
        'urls': [],
        'dates': [],
        'descriptions': [],
        'sources': []
    }

    try:
        root = etree.fromstring(response.content)
    except etree.XMLSyntaxError as e:
        logger.error(f"Error parsing XML: {e}")
        raise

    for item in root.findall('.//item'):
        title = item.findtext('title')
        if not title:
            continue
            
        lowercase_title = title.lower().split()
        if "AI" in title and any(word in lowercase_title for word in funding_keywords):
            title = title.split('-')[0] if '-' in title else title
            article_data['titles'].append(title)

            date = item.findtext('pubDate')
            article_data["dates"].append(date)

            description_html = item.findtext('description')
            html_tree = html.fromstring(description_html)
            anchor = html_tree.xpath('//a')
            if anchor:
                url = anchor[0].get('href')
                article_data['urls'].append(url)

                description = anchor[0].text.strip() if anchor[0].text else "N/A"
                article_data["descriptions"].append(description)
            else:
                article_data['urls'].append(item.findtext('link'))  # Fixed: was 'url'
                article_data['descriptions'].append("N/A")

            source = item.findtext('source')
            article_data["sources"].append(source)

    return article_data

async def main():
    start_time = time.perf_counter()
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        article_data = await fetch_rss_feed(client, URL)
        links_and_paragraphs = {
            'urls': article_data['urls'],
            'paragraphs': article_data['descriptions']
        }
        result = await finalize_ai_extraction(links_and_paragraphs)

    llm_results = None
    if result:
        llm_results = copy.deepcopy(funding_data_dict)

        for key, value_list in result.items():
            if key in llm_results and isinstance(value_list, list):
                llm_results[key].extend(value_list)
            elif key in llm_results:
                llm_results[key] = value_list

        urls = links_and_paragraphs.get("urls")
        llm_results["link"] = urls
        llm_results['article_date'].extend(article_data['dates'])
        llm_results['title'].extend(article_data['descriptions'])
        llm_results['source'].extend(article_data['sources'])

    else:
        logger.warning("AI extraction for Google News returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"Google News ran for {duration:.2f} seconds")
    return llm_results


if __name__ == "__main__":
    asyncio.run(main())

