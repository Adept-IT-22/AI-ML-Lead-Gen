import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from orchestration import normalization

@pytest.mark.asyncio
async def test_x(monkeypatch):
    # Prepare queues
    ingestion_to_normalization_queue = asyncio.Queue()
    normalization_to_enrichment_queue = asyncio.Queue()

    # Add mock data to ingestion queue
    await ingestion_to_normalization_queue.put(("eventbrite", {"type": "event", "link": ["l1"], "title": ["t1"], "city": ["c1"], "country": ["co1"], "tags": [["tag1"]], "event_id": ["e1"], "event_summary": ["s1"], "event_is_online": [True], "event_organizer_id": ["o1"]}))
    await ingestion_to_normalization_queue.put(("finsmes", {"type": "funding", "link": ["l2"], "title": ["t2"], "city": ["c2"], "country": ["co2"], "tags": [["tag2"]], "company_name": ["n2"], "company_decision_makers": [["d2"]], "company_decision_makers_position": [["p2"]], "funding_round": ["r2"], "amount_raised": [100], "currency": ["usd"], "investor_companies": [["ic2"]], "investor_people": [["ip2"]]}))
    await ingestion_to_normalization_queue.put(("hackernews", {"type": "hiring", "link": ["l3"], "title": ["t3"], "city": ["c3"], "country": ["co3"], "tags": [["tag3"]], "company_name": ["n3"], "company_decision_makers": [["d3"]], "company_decision_makers_position": [["p3"]], "job_roles": [["jr3"]], "hiring_reasons": [["hr3"]]}))

    # Patch asyncpg.create_pool to return a dummy pool
    dummy_pool = MagicMock()
    class DummyPoolContext:
        async def __aenter__(self): return dummy_pool
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(normalization.asyncpg, "create_pool", lambda **kwargs: DummyPoolContext())

    # Patch DB service functions
    monkeypatch.setattr(normalization, "is_data_in_db", AsyncMock(return_value=False))
    monkeypatch.setattr(normalization, "store_in_normalized_master", AsyncMock(return_value=1))
    monkeypatch.setattr(normalization, "store_in_normalized_events", AsyncMock())
    monkeypatch.setattr(normalization, "store_in_normalized_funding", AsyncMock())
    monkeypatch.setattr(normalization, "store_in_normalized_hiring", AsyncMock())

    # Patch normalization functions to just return the input data
    monkeypatch.setattr(normalization, "normalize_event_data", AsyncMock(side_effect=lambda d: d))
    monkeypatch.setattr(normalization, "normalize_funding_data", AsyncMock(side_effect=lambda d: d))
    monkeypatch.setattr(normalization, "normalize_hiring_data", AsyncMock(side_effect=lambda d: d))

    # Patch aiofiles.open to a dummy async context manager that records writes
    written = {}
    class DummyFile:
        async def write(self, data):
            written["data"] = data
    class DummyAiofiles:
        async def __aenter__(self): return DummyFile()
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(normalization.aiofiles, "open", lambda *a, **kw: DummyAiofiles())

    # Run the function
    await normalization.x(ingestion_to_normalization_queue, normalization_to_enrichment_queue)

    # Check that all data was normalized and written
    assert "data" in written
    assert '"type": "event"' in written["data"]
    assert '"type": "funding"' in written["data"]
    assert '"type": "hiring"' in written["data"]

    # Check that the normalized data was put in the enrichment queue
    result = await normalization_to_enrichment_queue.get()
    assert isinstance(result, list)
    assert any(item["type"] == "event" for item in result)
    assert any(item["type"] == "funding" for item in result)
    assert any(item["type"] == "hiring" for item in result)