import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../ingestion_module/hiring/hacker_news")))
from ingestion_module.hiring.hacker_news import fetch

@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    # Mock job IDs returned from fetch_hackernews_jobs
    job_ids = [123, 456]

    # Mock job details returned from get_all_job_details
    job_details = [
        {
            "by": "alice",
            "id": 123,
            "score": 10,
            "text": "AI job at AliceCorp",
            "time": 1700000000,
            "title": "AI Engineer",
            "url": "https://example.com/ai-job"
        },
        {
            "by": "bob",
            "id": 456,
            "score": 5,
            "text": "Non-AI job",
            "time": 1700000001,
            "title": "Backend Developer",
            "url": "https://example.com/backend-job"
        }
    ]

    # Patch fetch_hackernews_jobs to return job_ids
    monkeypatch.setattr(fetch, "fetch_hackernews_jobs", AsyncMock(return_value=job_ids))
    # Patch get_all_job_details to return job_details
    monkeypatch.setattr(fetch, "get_all_job_details", AsyncMock(return_value=job_details))
    # Patch finalize_ai_extraction to return extracted data
    extracted_data = {
        "company_name": ["AliceCorp"],
        "article_date": ["2025-10-10"],
        "title": ["AI Engineer"],
        "link": ["https://example.com/ai-job"]
    }
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(return_value=extracted_data))

    # Patch httpx.AsyncClient so it is not actually used
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())

    result = await fetch.main()
    assert result["source"] == "HackerNews"
    assert "AI Engineer" in result["title"]
    assert "AliceCorp" in result["company_name"]
    assert "https://example.com/ai-job" in result["link"]
    assert "company_decision_makers" in result

@pytest.mark.asyncio
async def test_main_no_extracted_data(monkeypatch):
    # Patch fetch_hackernews_jobs and get_all_job_details to return empty
    monkeypatch.setattr(fetch, "fetch_hackernews_jobs", AsyncMock(return_value=[]))
    monkeypatch.setattr(fetch, "get_all_job_details", AsyncMock(return_value=[]))
    # Patch finalize_ai_extraction to return empty dict
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(return_value={}))

    # Patch httpx.AsyncClient so it is not actually used
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())

    result = await fetch.main()
    # Should return None or a structure with empty lists
    assert result is None or all(isinstance(v, list) or isinstance(v, str) for v in result.values())