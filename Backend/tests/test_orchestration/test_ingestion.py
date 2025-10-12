import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../orchestration")))
from orchestration import ingestion

@pytest.mark.asyncio
async def test_run_ingestion_modules_all_success(monkeypatch):
    # Patch all ingestion module mains to return dummy dicts
    monkeypatch.setattr(ingestion, "finsmes_main", AsyncMock(return_value={"type": "funding", "source": "finsmes"}))
    monkeypatch.setattr(ingestion, "tech_eu_main", AsyncMock(return_value={"type": "funding", "source": "tech_eu"}))
    monkeypatch.setattr(ingestion, "techcrunch_main", AsyncMock(return_value={"type": "funding", "source": "techcrunch"}))
    monkeypatch.setattr(ingestion, "hacker_news_main", AsyncMock(return_value={"type": "hiring", "source": "hacker_news"}))
    monkeypatch.setattr(ingestion, "eventbrite_main", AsyncMock(return_value={"type": "event", "source": "eventbrite"}))

    # Patch wrap to just return (name, await coroutine)
    async def fake_wrap(name, coroutine):
        return (name, await coroutine)
    monkeypatch.setattr(ingestion, "wrap", fake_wrap)

    results = await ingestion.run_ingestion_modules()
    assert results["finsmes"]["source"] == "finsmes"
    assert results["tech_eu"]["source"] == "tech_eu"
    assert results["techcrunch"]["source"] == "techcrunch"
    assert results["hacker_news"]["source"] == "hacker_news"
    assert results["eventbrite"]["source"] == "eventbrite"

@pytest.mark.asyncio
async def test_run_ingestion_modules_with_exception(monkeypatch):
    # Patch some mains to raise, others to succeed
    monkeypatch.setattr(ingestion, "finsmes_main", AsyncMock(side_effect=Exception("fail")))
    monkeypatch.setattr(ingestion, "tech_eu_main", AsyncMock(return_value={"type": "funding", "source": "tech_eu"}))
    monkeypatch.setattr(ingestion, "techcrunch_main", AsyncMock(return_value={"type": "funding", "source": "techcrunch"}))
    monkeypatch.setattr(ingestion, "hacker_news_main", AsyncMock(return_value={"type": "hiring", "source": "hacker_news"}))
    monkeypatch.setattr(ingestion, "eventbrite_main", AsyncMock(return_value={"type": "event", "source": "eventbrite"}))

    async def fake_wrap(name, coroutine):
        try:
            return (name, await coroutine)
        except Exception as e:
            return (name, e)
    monkeypatch.setattr(ingestion, "wrap", fake_wrap)

    results = await ingestion.run_ingestion_modules()
    assert isinstance(results["finsmes"], Exception)
    assert results["tech_eu"]["source"] == "tech_eu"

@pytest.mark.asyncio
async def test_populate_queue(monkeypatch):
    # Patch run_ingestion_modules to return a mix of valid and invalid results
    monkeypatch.setattr(ingestion, "run_ingestion_modules", AsyncMock(return_value={
        "finsmes": {"type": "funding", "source": "finsmes"},
        "tech_eu": Exception("fail"),
        "eventbrite": {"type": "event", "source": "eventbrite"},
        "empty": {},
        "invalid": Exception("fail2")
    }))

    q = asyncio.Queue()
    q = await ingestion.populate_queue(q)
    results = []
    while not q.empty():
        results.append(await q.get())
    # Only valid dicts with "type" should be in the queue
    assert ("finsmes", {"type": "funding", "source": "finsmes"}) in results
    assert ("eventbrite", {"type": "event", "source": "eventbrite"}) in results
    assert all(isinstance(item[1], dict) and item[1].get("type") for item in results)