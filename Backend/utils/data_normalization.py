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

def normalize_company_decision_makers(decision_makers: List[str])->List[str]:
    if not decision_makers:
        return []
    
    normalized_decision_makers = []
    for decision_maker in decision_makers:
        clean_decision_maker = decision_makers.strip().lower()
        if clean_decision_maker:
            normalized_decision_makers.append(clean_decision_maker)

    return normalized_decision_makers