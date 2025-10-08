import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../normalization_module")))
from normalization_module import event_normalization

@pytest.mark.asyncio
async def test_normalize_event_data_success(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(event_normalization, "normalize_url", lambda url: f"normalized_{url}")
    monkeypatch.setattr(event_normalization, "normalize_date", lambda date: f"2025-01-01")
    monkeypatch.setattr(event_normalization, "normalize_country", lambda c: c.upper())
    monkeypatch.setattr(event_normalization, "normalize_city", lambda c: c.title())
    monkeypatch.setattr(event_normalization, "str_to_bool", lambda s: s == "true")
    monkeypatch.setattr(event_normalization, "normalize_tags", lambda t: t.lower() if isinstance(t, str) else [x.lower() for x in t])

    # Patch fetched_event_data to a known structure
    monkeypatch.setattr(event_normalization, "fetched_event_data", {
        "type": "",
        "source": "",
        "title": [],
        "link": [],
        "event_date": [],
        "country": [],
        "city": [],
        "event_id": [],
        "event_summary": [],
        "event_is_online": [],
        "tags": []
    })

    ingested_data = {
        "source": "eventbrite",
        "title": [" AI Summit "],
        "link": ["http://event.com/ai"],
        "event_date": ["2025-11-01"],
        "country": ["kenya"],
        "city": ["nairobi"],
        "event_id": [" 123 "],
        "event_summary": ["  The best AI event. "],
        "event_is_online": ["true"],
        "tags": [["AI", "Tech"]]
    }

    result = await event_normalization.normalize_event_data(ingested_data)
    assert result["type"] == "event"
    assert result["source"] == "eventbrite"
    assert result["title"] == ["AI Summit"]
    assert result["link"] == ["normalized_http://event.com/ai"]
    assert result["event_date"] == ["2025-01-01"]
    assert result["country"] == ["KENYA"]
    assert result["city"] == ["Nairobi"]
    assert result["event_id"] == ["123"]
    assert result["event_summary"] == ["The best AI event."]
    assert result["event_is_online"] == [True]
    assert result["tags"] == [["ai", "tech"]]

@pytest.mark.asyncio
async def test_normalize_event_data_empty():
    result = await event_normalization.normalize_event_data({})
    assert result == {}

@pytest.mark.asyncio
async def test_normalize_event_data_missing_fields(monkeypatch):
    # Patch normalization utils to return predictable values
    monkeypatch.setattr(event_normalization, "normalize_url", lambda url: url)
    monkeypatch.setattr(event_normalization, "normalize_date", lambda date: date)
    monkeypatch.setattr(event_normalization, "normalize_country", lambda c: c)
    monkeypatch.setattr(event_normalization, "normalize_city", lambda c: c)
    monkeypatch.setattr(event_normalization, "str_to_bool", lambda s: False)
    monkeypatch.setattr(event_normalization, "normalize_tags", lambda t: t)

    # Patch fetched_event_data to a known structure
    monkeypatch.setattr(event_normalization, "fetched_event_data", {
        "type": "",
        "source": "",
        "title": [],
        "link": [],
        "event_date": [],
        "country": [],
        "city": [],
        "event_id": [],
        "event_summary": [],
        "event_is_online": [],
        "tags": []
    })

    ingested_data = {
        "source": "eventbrite",
        # missing event_title, event_link, etc.
    }

    result = await event_normalization.normalize_event_data(ingested_data)
    assert result["type"] == "event"
    assert result["source"] == "eventbrite"
    assert result["title"] == []
    assert result["link"] == []
    assert result["event_date"] == []
    assert result["country"] == []
    assert result["city"] == []
    assert result["event_id"] == []
    assert result["event_summary"] == []
    assert result["event_is_online"] == []
    assert result["tags"] == []