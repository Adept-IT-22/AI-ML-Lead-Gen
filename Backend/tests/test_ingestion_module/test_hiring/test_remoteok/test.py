import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add Backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ingestion_module.hiring.remoteok import fetch

@pytest.mark.asyncio
async def test_fetch_jobs_success(monkeypatch):
    """Test successful job fetching from RemoteOK API"""
    mock_response_data = [
        {
            "id": "123",
            "title": "Software Engineer",
            "company": "TechCorp",
            "url": "https://remoteok.com/job/123",
            "description": "Great job",
            "date": "2025-12-01",
            "location": "Remote",
            "tags": ["python", "django"],
            "apply_url": "https://remoteok.com/apply/123"
        },
        {
            "legal": "Some legal text" # Should be filtered out
        }
    ]

    # Mock response context manager
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = mock_response_data

    # Mock session context manager
    mock_session = AsyncMock()
    # session.get is NOT async, it returns a context manager
    mock_session.get = Mock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Mock ClientSession constructor to return the session context manager
    # ClientSession() returns an object that is an async context manager
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    
    with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
        jobs = await fetch.fetch_jobs()
        
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[0]["company"] == "TechCorp"

@pytest.mark.asyncio
async def test_fetch_jobs_failure(monkeypatch):
    """Test job fetching failure"""
    mock_response = AsyncMock()
    mock_response.status = 500
    
    mock_session = AsyncMock()
    mock_session.get = Mock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session

    with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
        jobs = await fetch.fetch_jobs()
        
    assert len(jobs) == 0

def test_normalize_job_data():
    """Test job data normalization"""
    raw_job = {
        "id": 123, # Int ID
        "title": "Dev",
        "company": "Comp",
        "url": "http://url",
        "description": "Desc",
        "date": "2025-01-01",
        "location": "World",
        "tags": ["a", "b"],
        "apply_url": "http://apply"
    }
    
    normalized = fetch.normalize_job_data(raw_job)
    
    assert normalized["id"] == "123" # Should be string
    assert normalized["title"] == "Dev"
    assert normalized["tags"] == ["a", "b"]

@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    """Test main function flow"""
    
    # Mock fetch_jobs
    async def mock_fetch_jobs():
        return [{
            "id": "1",
            "title": "Job 1",
            "company": "Comp 1",
            "url": "url1",
            "description": "desc1",
            "date": "date1",
            "location": "loc1",
            "tags": ["tag1"],
            "apply_url": "apply1"
        }]
    
    monkeypatch.setattr(fetch, "fetch_jobs", mock_fetch_jobs)
    
    # Mock finalize_ai_extraction
    async def mock_ai_extraction(data):
        return {
            "company_decision_makers": [["DM1"]],
            "hiring_reasons": [["Reason1"]],
            "job_roles": [["Role1"]],
            "tags": [["Tag1"]]
        }
    
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_extraction)
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "remoteok"
    assert len(result["title"]) == 1
    assert result["title"][0] == "Job 1"
    assert result["company_decision_makers"][0] == ["DM1"]

@pytest.mark.asyncio
async def test_main_no_jobs(monkeypatch):
    """Test main function when no jobs found"""
    
    async def mock_fetch_jobs():
        return []
    
    monkeypatch.setattr(fetch, "fetch_jobs", mock_fetch_jobs)
    
    result = await fetch.main()
    
    assert result is None
