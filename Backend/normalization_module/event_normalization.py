from utils.data_normalization import *
from utils.data_structures.events_data_structure import *
from typing import Dict, List, Any
from dateutil.parser import parse
import logging
import json
import copy

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


"""
ingested_data below looks like this:
    {"eventbrite": {
        "type": "event",
        "source": "eventbrite",
        "event_links": ["...", "..."],
        etc.
        }
    }
"""

async def normalize_event_data(ingested_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    if not ingested_data:
        logger.error("No event data to normalize. Ingested data is empty")
        return {}
    
    #Make a deep copy of the events_data_structure
    logger.info("Normalizing event data")
    normalized_event_data = copy.deepcopy(fetched_event_data)

    normalized_event_data.update({
        "type": "event",
        "source": ingested_data.get("source"),
        "event_title": [title.strip() for title in ingested_data.get("event_title", [])],
        "event_link": [normalize_url(url) for url in ingested_data.get("event_link", [])],
        "event_date": [str(normalize_date(date)) for date in ingested_data.get("event_date", [])],
        "event_country": [normalize_country(country) for country in ingested_data.get("event_country", [])],
        "event_city": [normalize_city(city) for city in ingested_data.get("event_city", [])],
        "event_id": [eid.strip() for eid in ingested_data.get("event_id", [])],
        "event_summary": [summary.strip() for summary in ingested_data.get("event_summary", [])],
        "event_is_online": [str(status) for status in ingested_data.get("event_is_online", [])],
        "event_tags": [normalize_tags(tag) for tag in ingested_data.get("event_tags")]
    })

    logger.info("Normalizing event data")
    return normalized_event_data

