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

def normalize_funding_data(ingested_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    if not ingested_data:
        logger.error("No data to normalize. Ingested data is empty")
        return {}
    
    #Make a deep copy of the events_data_structure
    normalized_data: Dict[str, FundingData] = {}
    normalized_funding_data: FundingData = copy.deepcopy(fetched_funding_data)

    for name, funding_data in ingested_data.items():
        normalized_funding_data.update({
            "type": "funding",
            "source": funding_data.get("source"),
            "article_title": [title.strip() for title in funding_data.get("article_title", [])],
            "article_link": [normalize_url(url) for url in funding_data.get("article_link", [])],
            "article_date": [str(normalize_date(date)) for date in funding_data.get("article_date", [])],
            "company_name": [name.strip().title() for name in funding_data.get("company_name", [])],
            "company_city": [normalize_city(city) for city in funding_data.get("company_city", [])],
            "company_country": [normalize_country(country) for country in funding_data.get("company_country", [])],
            "company_decision_makers": [normalize_company_decision_makers(decision_maker_list) for decision_maker_list in funding_data.get("company_decision_makers", [])],
            "company_decision_makers_position": [normalize_company_decision_makers(decision_maker_position_list) for decision_maker_position_list in funding_data.get("company_decision_makers_position", [])],
            "funding_round": [fround.strip().title() for fround in funding_data.get("funding_round", [])],
            "amount_raised": [normalize_amount_raised(amount_raised) for amount_raised in funding_data.get("amount_raised", [])],
            "currency": [normalize_currency(currency) for currency in funding_data.get("currency", [])],
            "investor_companies": [normalize_company_decision_makers(investor_company_list) for investor_company_list in funding_data.get("investor_companies", [])],
            "investor_people": [normalize_company_decision_makers(investor_people_list) for investor_people_list in funding_data.get("investor_people", [])],
            "tags": [normalize_tags(tag) for tag in funding_data.get("tags")]
        })
        normalized_data[name] = normalized_funding_data

    return normalized_data

x = {
    "y": {
  "type": "funding",
  "source": "Tech.EU",
  "article_title": [
    "Bisly Raises \u20ac4.3M to Expand AI Building Automation in Europe"
  ],
  "article_link": [
    "https://tech.eu/2025/08/06/bisly-raises-eur43m-to-expand-ai-building-automation-in-europe//"
  ],
  "article_date": [
    "2025-08-06"
  ],
  "company_name": [
    "Bisly"
  ],
  "company_city": [
    "Tallinn"
  ],
  "company_country": [
    "Estonia"
  ],
  "company_decision_makers": [
    [
      "Ants Vill"
    ]
  ],
  "company_decision_makers_position": [
    [
      "CEO",
      "co-founder"
    ]
  ],
  "funding_round": [
    "Funding Round"
  ],
  "amount_raised": [
    "\u20ac4.3 million"
  ],
  "currency": [
    "EUR"
  ],
  "investor_companies": [
    [
      "2C Ventures",
      "Aconterra",
      "Pinorena",
      "Foxway",
      "SmartCap"
    ]
  ],
  "investor_people": [
    [
      "Martin Koppel"
    ]
  ],
  "tags": [
    [
      "AI",
      "building automation",
      "smart building",
      "energy efficiency",
      "climate tech",
      "Estonia",
      "Europe",
      "expansion"
    ]
  ]
}
}

a = normalize_funding_data(x)
print(json.dumps(a, indent=2))