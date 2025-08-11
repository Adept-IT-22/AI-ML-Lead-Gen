import re
import pycountry
from dateutil.parser import parse
from typing import Dict, List, Any

OVERRIDES = {
    "america": "America",
    "us": "America",
    "usa": "America",
    "u.s.": "America",
    "u.s.a.": "America",
    "united states of america": "America",
}

def normalize_country(country: str) -> str:
    if not country:
        return ""

    cleaned = country.strip().lower()
    if cleaned in OVERRIDES:
        return OVERRIDES[cleaned]

    try:
        match = pycountry.countries.search_fuzzy(query=country)
        return match[0].name
    except LookupError:
        return country.strip().title()

def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    
    try:
       now = parse(date_str) 
       return now.date()
    except:
        return date_str.strip()

def normalize_city(city: str) -> str:
    if not city:
        return ""
    
    return city.replace("_", " ").strip().title()

def normalize_url(url: str)->str:
    if not url:
        return ""
    
    return url.strip().lower()

def normalize_tags(tags: List[str])->List[str]:
    if not tags:
        return []
    
    seen = set()
    normalized_tags = []
    for tag in tags:
        clean_tag = tag.strip().lower()
        if clean_tag and not clean_tag not in seen:
            seen.add(clean_tag)
            normalized_tags.append(clean_tag)

    return normalized_tags

def normalize_company_decision_makers(decision_makers: str|List[str])->List[str]:
    if not decision_makers:
        return []
    
    normalized_decision_makers = []
    if isinstance(decision_makers, List):
        for decision_maker in decision_makers:
            clean_decision_maker = decision_maker.strip().title()
            if clean_decision_maker:
                normalized_decision_makers.append(clean_decision_maker)

    elif isinstance(decision_makers, str):
        normalized_decision_makers.append(decision_makers.strip().title())

    return normalized_decision_makers

def normalize_currency(currency: str)->str:
    if not currency:
        return "" 
    
    try: 
        normalized_currency = pycountry.currencies.lookup(currency)
        return normalize_currency.name
    except:
        return currency.strip().lower()

def normalize_amount_raised(amount_raised: str) -> str:
    if not amount_raised:
        return ""

    try:
        match = re.search(r'(\d+(?:\.\d+)?)\s*(M|B|K|Million|Billion|Thousand)', amount_raised, re.IGNORECASE)
        if match:
            number = float(match.group(1))
            unit = match.group(2).lower()

            multipliers = {
                'k': 1_000,
                'thousand': 1_000,
                'm': 1_000_000,
                'million': 1_000_000,
                'b': 1_000_000_000,
                'billion': 1_000_000_000
            }

            normalized = int(number * multipliers[unit])
            return str(normalized)
    except:
        pass

    return amount_raised.strip()
