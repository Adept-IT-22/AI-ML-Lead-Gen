from utils.data_normalization import *
from utils.data_structures.hiring_data_structure import *
from typing import Dict, List, Any
import logging
import copy
import json

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

"""
ingested_data below looks like this:
    {"hackernews": {
        "type": "hiring",
        "source": "hackernews",
        "article_link": ["...", "..."],
        etc.
        }
    }
"""

async def normalize_hiring_data(ingested_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    if not ingested_data:
        logger.error("No hiring data to normalize. Ingested data is empty")
        return {}
    
    #Make a deep copy of the events_data_structure
    logger.info("Normalizing hiring data")
    normalized_hiring_data = copy.deepcopy(fetched_hiring_data)

    normalized_hiring_data.update({
        "type": "hiring",
        "source": ingested_data.get("source", ""),
        "article_id": [str(aid) for aid in ingested_data.get("article_id", [])],
        "title": [title.strip() for title in ingested_data.get("title", [])],
        "link": [normalize_url(url) for url in ingested_data.get("link", [])],
        "article_date": [str(normalize_date(date)) for date in ingested_data.get("article_date", [])],
        "company_name": [name.strip().lower() for name in ingested_data.get("company_name", [])],
        "city": [normalize_city(city) for city in ingested_data.get("city", [])],
        "country": [normalize_country(country) for country in ingested_data.get("country", [])],
        "company_decision_makers": [normalize_company_decision_makers(decision_maker_list) for decision_maker_list in ingested_data.get("company_decision_makers", [])],
        "company_decision_makers_position": [normalize_company_decision_makers(decision_maker_position_list) for decision_maker_position_list in ingested_data.get("company_decision_makers_position", [])],
        "job_roles": [normalize_company_decision_makers(job_role_list) for job_role_list in ingested_data.get("job_roles", [])],
        "hiring_reasons": [normalize_company_decision_makers(hiring_reasons_list) for hiring_reasons_list in ingested_data.get("hiring_reasons", [])],
        "tags": [normalize_tags(tag) for tag in ingested_data.get("tags", [])],
        "painpoints": [normalize_tags(painpoint) for painpoint in ingested_data.get("painpoints", [])]
    })

    logger.info("Normalizing hiring data")
    return normalized_hiring_data
