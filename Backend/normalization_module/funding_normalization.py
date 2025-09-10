from utils.data_normalization import *
from utils.data_structures.news_data_structure import *
from typing import Dict, List, Any
import logging
import copy
import json

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


"""
ingested_data below looks like this:
    {"finsmes": {
        "type": "funding",
        "source": "finsmes",
        "article_link": ["...", "..."],
        etc.
        }
    }
"""

async def normalize_funding_data(ingested_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    if not ingested_data:
        logger.error("No funding data to normalize. Ingested data is empty")
        return {}
    
    #Make a deep copy of the events_data_structure
    logger.info("Normalizing funding data")
    normalized_funding_data = copy.deepcopy(fetched_funding_data)

    normalized_funding_data.update({
        "type": "funding",
        "source": ingested_data.get("source", ""),
        "title": [title.strip() for title in ingested_data.get("title", [])],
        "link": [normalize_url(url) for url in ingested_data.get("link", [])],
        "article_date": [str(normalize_date(date)) for date in ingested_data.get("article_date", [])],
        "company_name": [name.strip().lower() for name in ingested_data.get("company_name", [])],
        "city": [normalize_city(city) for city in ingested_data.get("city", [])],
        "country": [normalize_country(country) for country in ingested_data.get("country", [])],
        "company_decision_makers": [normalize_company_decision_makers(decision_maker_list) for decision_maker_list in ingested_data.get("company_decision_makers", [])],
        "company_decision_makers_position": [normalize_company_decision_makers(decision_maker_position_list) for decision_maker_position_list in ingested_data.get("company_decision_makers_position", [])],
        "funding_round": [fround.strip().title() for fround in ingested_data.get("funding_round", [])],
        "amount_raised": [normalize_amount_raised(amount_raised) for amount_raised in ingested_data.get("amount_raised", [])],
        "currency": [normalize_currency(currency) for currency in ingested_data.get("currency", [])],
        "investor_companies": [normalize_company_decision_makers(investor_company_list) for investor_company_list in ingested_data.get("investor_companies", [])],
        "investor_people": [normalize_company_decision_makers(investor_people_list) for investor_people_list in ingested_data.get("investor_people", [])],
        "tags": [normalize_tags(tag) for tag in ingested_data.get("tags", [])]
    })

    logger.info("Done normalizing funding data")
    return normalized_funding_data
