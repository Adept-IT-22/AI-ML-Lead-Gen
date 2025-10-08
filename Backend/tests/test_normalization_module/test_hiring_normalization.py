import pytest
import pytest_asyncio

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../normalization_module")))
from normalization_module import hiring_normalization

@pytest.mark.asyncio
async def test_normalize_hiring_data_success(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(hiring_normalization, "normalize_url", lambda url: f"normalized_{url}")
    monkeypatch.setattr(hiring_normalization, "normalize_date", lambda date: "2025-01-01")
    monkeypatch.setattr(hiring_normalization, "normalize_city", lambda c: c.title())
    monkeypatch.setattr(hiring_normalization, "normalize_country", lambda c: c.upper())
    monkeypatch.setattr(hiring_normalization, "normalize_company_decision_makers", lambda l: [x.upper() for x in l])
    monkeypatch.setattr(hiring_normalization, "normalize_tags", lambda t: t.lower() if isinstance(t, str) else [x.lower() for x in t])

    # Patch fetched_hiring_data to a known structure
    monkeypatch.setattr(hiring_normalization, "fetched_hiring_data", {
        "type": "",
        "source": "",
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
        "tags": []
    })

    ingested_data = {
        "source": "hackernews",
        "article_id": [123],
        "title": [" AI Engineer "],
        "link": ["http://hiring.com/ai"],
        "article_date": ["2025-11-01"],
        "company_name": [" OpenAI "],
        "city": ["nairobi"],
        "country": ["kenya"],
        "company_decision_makers": [["alice", "bob"]],
        "company_decision_makers_position": [["ceo", "cto"]],
        "job_roles": [["engineer", "scientist"]],
        "hiring_reasons": [["expansion"]],
        "tags": [["AI", "Tech"]]
    }

    result = await hiring_normalization.normalize_hiring_data(ingested_data)
    assert result["type"] == "hiring"
    assert result["source"] == "hackernews"
    assert result["article_id"] == ["123"]
    assert result["title"] == ["AI Engineer"]
    assert result["link"] == ["normalized_http://hiring.com/ai"]
    assert result["article_date"] == ["2025-01-01"]
    assert result["company_name"] == ["openai"]
    assert result["city"] == ["Nairobi"]
    assert result["country"] == ["KENYA"]
    assert result["company_decision_makers"] == [["ALICE", "BOB"]]
    assert result["company_decision_makers_position"] == [["CEO", "CTO"]]
    assert result["job_roles"] == [["ENGINEER", "SCIENTIST"]]
    assert result["hiring_reasons"] == [["EXPANSION"]]
    assert result["tags"] == [["ai", "tech"]]

@pytest.mark.asyncio
async def test_normalize_hiring_data_empty():
    result = await hiring_normalization.normalize_hiring_data({})
    assert result == {}

@pytest.mark.asyncio
async def test_normalize_hiring_data_missing_fields(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(hiring_normalization, "normalize_url", lambda url: url)
    monkeypatch.setattr(hiring_normalization, "normalize_date", lambda date: date)
    monkeypatch.setattr(hiring_normalization, "normalize_city", lambda c: c)
    monkeypatch.setattr(hiring_normalization, "normalize_country", lambda c: c)
    monkeypatch.setattr(hiring_normalization, "normalize_company_decision_makers", lambda l: l)
    monkeypatch.setattr(hiring_normalization, "normalize_tags", lambda t: t)

    # Patch fetched_hiring_data to a known structure
    monkeypatch.setattr(hiring_normalization, "fetched_hiring_data", {
        "type": "",
        "source": "",
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
        "tags": []
    })

    ingested_data = {
        "source": "hackernews",
        # missing most fields
    }

    result = await hiring_normalization.normalize_hiring_data(ingested_data)
    assert result["type"] == "hiring"
    assert result["source"] == "hackernews"
    assert result["article_id"] == []
    assert result["title"] == []
    assert result["link"] == []
    assert result["article_date"] == []
    assert result["company_name"] == []
    assert result["city"] == []
    assert result["country"] == []
    assert result["company_decision_makers"] == []
    assert result["company_decision_makers_position"] == []
    assert result["job_roles"] == []
    assert result["hiring_reasons"] == []
    assert result["tags"] == []