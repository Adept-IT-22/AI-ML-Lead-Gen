import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add Backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable for AI extraction
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.himalayas.fetch import fetch_jobs, main

@pytest.mark.asyncio
async def test_fetch_jobs_success():
    """Test successful fetching of jobs from Himalayas."""
    mock_data = {
        "jobs": [
            {"id": "1", "title": "Developer", "description": "desc"},
            {"id": "2", "title": "CFO", "description": "finance"}
        ]
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await fetch_jobs()
        assert result == mock_data
        assert "jobs" in result

@pytest.mark.asyncio
async def test_himalayas_main_orchestration():
    """Test the main orchestration and filtering of Himalayas fetcher."""
    mock_api_data = {
        "jobs": [
            {
                "id": "1",
                "title": "Senior Python Developer",
                "company_name": "Tech Corp",
                "description": "We need a Python dev.",
                "application_link": "https://himalayas.app/jobs/python-dev"
            },
            {
                "id": "2",
                "title": "Sales Representative",
                "company_name": "Sales Corp",
                "description": "Sales role, selling products.",
                "application_link": "https://himalayas.app/jobs/sales"
            }
        ]
    }
    
    mock_ai_results = {
        "company_decision_makers": [["CEO"]],
        "hiring_reasons": [["Expansion"]],
        "job_roles": [["Backend Developer"]],
        "tags": [["Python"]],
        "city": ["New York"],
        "country": ["USA"]
    }

    with patch("ingestion_module.hiring.himalayas.fetch.fetch_jobs", return_value=mock_api_data):
        with patch("ingestion_module.hiring.himalayas.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "Himalayas"
            # Should have filtered to only Python Developer
            assert len(results["title"]) == 1
            assert results["title"][0] == "Senior Python Developer"
            assert results["company_name"][0] == "Tech Corp"
            # Check if AI data merged
            assert results["job_roles"][0] == ["Backend Developer"]
            assert results["city"][0] == "New York"
