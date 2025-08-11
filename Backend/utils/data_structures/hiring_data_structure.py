from typing import TypedDict, List

class HiringData(TypedDict):
    type: str
    source: str
    article_id: List[str]
    article_title: List[str]
    article_link: List[str]
    article_date: List[str]
    company_name: List[str]
    company_city: List[str]
    company_country: List[str]
    company_decision_makers: List[List[str]]
    company_decision_makers_position: List[List[str]]
    job_roles: List[List[str]]
    hiring_reasons: List[List[str]]
    tags: List[List[str]]

fetched_hiring_data = {
    "type": "hiring",
    "source": [],
    "article_id": [],
    "article_title": [],
    "article_link": [],
    "article_date": [],
    "company_name": [],
    "company_city": [],
    "company_country": [],
    "company_decision_makers": [],
    "company_decision_makers_position": [],
    "job_roles": [],
    "hiring_reasons": [],
    "tags": []
}