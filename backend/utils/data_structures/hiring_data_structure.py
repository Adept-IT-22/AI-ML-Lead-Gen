from typing import TypedDict, List

class HiringData(TypedDict):
    type: str
    source: str
    article_id: List[str]
    title: List[str]
    link: List[str]
    article_date: List[str]
    company_name: List[str]
    city: List[str]
    country: List[str]
    company_decision_makers: List[List[str]]
    company_decision_makers_position: List[List[str]]
    job_roles: List[List[str]]
    hiring_reasons: List[List[str]]
    tags: List[List[str]]
    painpoints: List[List[str]]
    service: List[str]

fetched_hiring_data = {
    "type": "hiring",
    "source": [],
    "article_id": [],
    "title": [],
    "link": [],
    "article_date": [],
    "company_name": [],
    "city": [],
    "country": [],
    "company_decision_makers": [],
    "company_decision_makers_position": [],
    "job_roles": [],
    "hiring_reasons": [],
    "tags": [],
    "painpoints": [],
    "service": [],
}