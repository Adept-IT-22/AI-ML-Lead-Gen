import pytest
import pytest_asyncio

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../normalization_module")))
from normalization_module import funding_normalization

@pytest.mark.asyncio
async def test_normalize_funding_data_success(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(funding_normalization, "normalize_url", lambda url: f"normalized_{url}")
    monkeypatch.setattr(funding_normalization, "normalize_date", lambda date: "2025-01-01")
    monkeypatch.setattr(funding_normalization, "normalize_city", lambda c: c.title())
    monkeypatch.setattr(funding_normalization, "normalize_country", lambda c: c.upper())
    monkeypatch.setattr(funding_normalization, "normalize_company_decision_makers", lambda l: [x.upper() for x in l])
    monkeypatch.setattr(funding_normalization, "normalize_amount_raised", lambda a: float(a) if a else 0.0)
    monkeypatch.setattr(funding_normalization, "normalize_currency", lambda c: c.upper())
    monkeypatch.setattr(funding_normalization, "normalize_tags", lambda t: t.lower() if isinstance(t, str) else [x.lower() for x in t])

    # Patch fetched_funding_data to a known structure
    monkeypatch.setattr(funding_normalization, "fetched_funding_data", {
        "type": "",
        "source": "",
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
        "tags": []
    })

    ingested_data = {
        "source": "finsmes",
        "title": [" AI Funding "],
        "link": ["http://funding.com/ai"],
        "article_date": ["2025-11-01"],
        "company_name": [" OpenAI "],
        "city": ["nairobi"],
        "country": ["kenya"],
        "company_decision_makers": [["alice", "bob"]],
        "company_decision_makers_position": [["ceo", "cto"]],
        "funding_round": ["seed"],
        "amount_raised": ["1000000"],
        "currency": ["usd"],
        "investor_companies": [["Sequoia", "Accel"]],
        "investor_people": [["John Doe"]],
        "tags": [["AI", "Tech"]]
    }

    result = await funding_normalization.normalize_funding_data(ingested_data)
    assert result["type"] == "funding"
    assert result["source"] == "finsmes"
    assert result["title"] == ["AI Funding"]
    assert result["link"] == ["normalized_http://funding.com/ai"]
    assert result["article_date"] == ["2025-01-01"]
    assert result["company_name"] == ["openai"]
    assert result["city"] == ["Nairobi"]
    assert result["country"] == ["KENYA"]
    assert result["company_decision_makers"] == [["ALICE", "BOB"]]
    assert result["company_decision_makers_position"] == [["CEO", "CTO"]]
    assert result["funding_round"] == ["Seed"]
    assert result["amount_raised"] == [1000000.0]
    assert result["currency"] == ["USD"]
    assert result["investor_companies"] == [["SEQUOIA", "ACCEL"]]
    assert result["investor_people"] == [["JOHN DOE"]]
    assert result["tags"] == [["ai", "tech"]]

@pytest.mark.asyncio
async def test_normalize_funding_data_empty():
    result = await funding_normalization.normalize_funding_data({})
    assert result == {}

@pytest.mark.asyncio
async def test_normalize_funding_data_missing_fields(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(funding_normalization, "normalize_url", lambda url: url)
    monkeypatch.setattr(funding_normalization, "normalize_date", lambda date: date)
    monkeypatch.setattr(funding_normalization, "normalize_city", lambda c: c)
    monkeypatch.setattr(funding_normalization, "normalize_country", lambda c: c)
    monkeypatch.setattr(funding_normalization, "normalize_company_decision_makers", lambda l: l)
    monkeypatch.setattr(funding_normalization, "normalize_amount_raised", lambda a: a)
    monkeypatch.setattr(funding_normalization, "normalize_currency", lambda c: c)
    monkeypatch.setattr(funding_normalization, "normalize_tags", lambda t: t)

    # Patch fetched_funding_data to a known structure
    monkeypatch.setattr(funding_normalization, "fetched_funding_data", {
        "type": "",
        "source": "",
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
        "tags": []
    })

    ingested_data = {
        "source": "finsmes",
        # missing most fields
    }

    result = await funding_normalization.normalize_funding_data(ingested_data)
    assert result["type"] == "funding"
    assert result["source"] == "finsmes"
    assert result["title"] == []
    assert result["link"] == []
    assert result["article_date"] == []
    assert result["company_name"] == []
    assert result["city"] == []
    assert result["country"] == []
    assert result["company_decision_makers"] == []
    assert result["company_decision_makers_position"] == []
    assert result["funding_round"] == []
    assert result["amount_raised"] == []
    assert result["currency"] == []
    assert result["investor_companies"] == []
    assert result["investor_people"] == []
    assert result["tags"] == []