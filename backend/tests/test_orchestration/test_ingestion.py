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
    # Patch the currently active ingestion module mains to return dummy dicts
    monkeypatch.setattr(ingestion, "pr_news_wire_main", AsyncMock(return_value={"type": "funding", "source": "pr_news_wire"}))
    monkeypatch.setattr(ingestion, "djinni_main", AsyncMock(return_value={"type": "hiring", "source": "djinni"}))

    # Patch wrap to just return (name, await coroutine)
    async def fake_wrap(name, coroutine):
        return (name, await coroutine)
    monkeypatch.setattr(ingestion, "wrap", fake_wrap)

    results = await ingestion.run_ingestion_modules()
    assert results["pr_news_wire"]["source"] == "pr_news_wire"
    assert results["djinni"]["source"] == "djinni"

@pytest.mark.asyncio
async def test_run_ingestion_modules_with_exception(monkeypatch):
    # Patch one to raise, the other to succeed
    monkeypatch.setattr(ingestion, "pr_news_wire_main", AsyncMock(side_effect=Exception("fail")))
    monkeypatch.setattr(ingestion, "djinni_main", AsyncMock(return_value={"type": "hiring", "source": "djinni"}))

    async def fake_wrap(name, coroutine):
        try:
            return (name, await coroutine)
        except Exception as e:
            return (name, e)
    monkeypatch.setattr(ingestion, "wrap", fake_wrap)

    results = await ingestion.run_ingestion_modules()
    assert isinstance(results["pr_news_wire"], Exception)
    assert results["djinni"]["source"] == "djinni"

@pytest.mark.asyncio
async def test_populate_queue(monkeypatch):
    # Patch run_ingestion_modules to return a mix of valid and invalid results
    monkeypatch.setattr(ingestion, "run_ingestion_modules", AsyncMock(return_value={
        "pr_news_wire": {"type": "funding", "source": "pr_news_wire"},
        "djinni": Exception("fail"),
        "empty": {},
        "invalid": Exception("fail2")
    }))

    q = asyncio.Queue()
    q = await ingestion.populate_queue(q)
    results = []
    while not q.empty():
        results.append(await q.get())
    # Only valid dicts with "type" should be in the queue
    assert ("pr_news_wire", {"type": "funding", "source": "pr_news_wire"}) in results
    assert all(isinstance(item[1], dict) and item[1].get("type") for item in results)