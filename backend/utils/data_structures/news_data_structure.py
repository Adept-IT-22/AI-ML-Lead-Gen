from typing import TypedDict, List

class FundingData(TypedDict):
    type: str
    source: str
    title: List[str]
    link: List[str]
    article_date: List[str]
    company_name: List[str]
    city: List[str]
    country: List[str]
    company_decision_makers: List[List[str]]
    company_decision_makers_position: List[List[str]]
    funding_round: List[str]
    amount_raised: List[str]
    currency: List[str]
    investor_companies: List[List[str]]
    investor_people: List[List[str]]
    tags: List[List[str]]
    painpoints: List[List[str]]
    service: List[str]

fetched_funding_data = {
    "type": "funding",
    "source": [],
    "title": [],
    "link": [],
    "article_date": [],
    "company_name": [],
    "city": [],
    "country": [],
    "company_decision_makers": [],
    "company_decision_makers_position": [],
    "funding_round": [],
    "amount_raised": [],
    "currency": [],
    "investor_companies": [],
    "investor_people": [],
    "tags": [],
    "painpoints": [],
    "service": []
}