import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add Backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ingestion_module.hiring.active_jobs_db import fetch


@pytest.mark.asyncio
async def test_fetch_jobs_from_api_success(monkeypatch):
    """Test successful API call to Active Jobs DB"""
    # Mock API response
    mock_jobs = [
        {
            "id": "job123",
            "title": "Software Engineer",
            "organization": "TechCorp",
            "url": "https://example.com/job1",
            "date_posted": "2025-11-01T10:00:00",
            "locations_derived": [{"city": "Berlin", "country": "Germany"}],
            "ai_key_skills": ["Python", "AWS"],
            "ai_taxonomies_a": ["Technology", "Software"],
            "ai_hiring_manager_name": "John Doe",
            "ai_core_responsibilities": "Build scalable systems"
        },
        {
            "id": "job456",
            "title": "Backend Developer",
            "organization": "StartupXYZ",
            "url": "https://example.com/job2",
            "date_posted": "2025-11-02T10:00:00",
            "locations_derived": [{"city": "Warsaw", "country": "Poland"}],
            "ai_key_skills": ["Java", "Docker"],
            "ai_taxonomies_a": ["Technology"],
            "ai_hiring_manager_name": None,
            "ai_core_responsibilities": "Develop APIs"
        }
    ]
    
    # Mock httpx response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_jobs
    mock_response.headers = {
        "x-ratelimit-jobs-remaining": "100",
        "x-ratelimit-requests-remaining": "50"
    }
    mock_response.raise_for_status = MagicMock()
    
    # Mock AsyncClient
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    
    result = await fetch.fetch_jobs_from_api(mock_client, "Software", "Germany")
    
    assert len(result) == 2
    assert result[0]["id"] == "job123"
    assert result[1]["organization"] == "StartupXYZ"


@pytest.mark.asyncio
async def test_fetch_jobs_from_api_http_error(monkeypatch):
    """Test API error handling"""
    import httpx
    
    # Mock httpx error response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response))
    
    result = await fetch.fetch_jobs_from_api(mock_client, "Software", "Germany")
    
    assert result == []


@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    """Test full main function with mocked API and LLM"""
    # Mock API response
    mock_jobs = [
        {
            "id": "job123",
            "title": "Software Engineer",
            "organization": "TechCorp",
            "url": "https://example.com/job1",
            "date_posted": "2025-11-01T10:00:00",
            "locations_derived": [{"city": "Berlin", "country": "Germany"}],
            "ai_key_skills": ["Python", "AWS"],
            "ai_taxonomies_a": ["Technology", "Software"],
            "ai_hiring_manager_name": "John Doe",
            "ai_core_responsibilities": "Build scalable systems"
        }
    ]
    
    # Mock fetch_jobs_from_api
    monkeypatch.setattr(fetch, "fetch_jobs_from_api", AsyncMock(return_value=mock_jobs))
    
    # Mock LLM extraction
    extracted_data = {
        "company_decision_makers": [["John Doe", "CTO"]],
        "hiring_reasons": [["Team expansion"]],
        "job_roles": [["Software Engineer"]]
    }
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(return_value=extracted_data))
    
    # Mock os.getenv to return a fake API key
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    
    # Mock httpx.AsyncClient
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "Active Jobs DB"
    assert result["type"] == "hiring"
    assert len(result["title"]) == 1
    assert "Software Engineer" in result["title"]
    assert "TechCorp" in result["company_name"]
    assert "https://example.com/job1" in result["link"]
    assert "Berlin" in result["city"]
    assert "Germany" in result["country"]


@pytest.mark.asyncio
async def test_main_no_api_key(monkeypatch):
    """Test main function without GEMINI_API_KEY (should still work with API data only)"""
    mock_jobs = [
        {
            "id": "job123",
            "title": "Software Engineer",
            "organization": "TechCorp",
            "url": "https://example.com/job1",
            "date_posted": "2025-11-01T10:00:00",
            "locations_derived": [{"city": "Berlin", "country": "Germany"}],
            "ai_key_skills": ["Python"],
            "ai_taxonomies_a": ["Technology"],
            "ai_hiring_manager_name": None,
            "ai_core_responsibilities": None
        }
    ]
    
    monkeypatch.setattr(fetch, "fetch_jobs_from_api", AsyncMock(return_value=mock_jobs))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "Active Jobs DB"
    assert len(result["title"]) == 1


@pytest.mark.asyncio
async def test_main_no_jobs_found(monkeypatch):
    """Test when API returns no jobs"""
    monkeypatch.setattr(fetch, "fetch_jobs_from_api", AsyncMock(return_value=[]))
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())
    
    result = await fetch.main()
    
    assert result is None


@pytest.mark.asyncio
async def test_main_handles_string_location(monkeypatch):
    """Test handling of location_derived as string instead of dict"""
    mock_jobs = [
        {
            "id": "job123",
            "title": "Software Engineer",
            "organization": "TechCorp",
            "url": "https://example.com/job1",
            "date_posted": "2025-11-01T10:00:00",
            "locations_derived": ["Germany"],  # String in list instead of dict
            "ai_key_skills": [],
            "ai_taxonomies_a": [],
            "ai_hiring_manager_name": None,
            "ai_core_responsibilities": None
        }
    ]
    
    monkeypatch.setattr(fetch, "fetch_jobs_from_api", AsyncMock(return_value=mock_jobs))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(fetch.httpx, "AsyncClient", MagicMock())
    
    result = await fetch.main()
    
    assert result is not None
    # Should handle the string gracefully
    assert len(result["title"]) == 1
