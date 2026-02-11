import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add Backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.arbeitnow.fetch import fetch_jobs, main

@pytest.mark.asyncio
async def test_fetch_jobs_success():
    """Test successful fetching from Arbeitnow."""
    mock_data = {
        "data": [
            {"slug": "job-1", "title": "Dev", "company_name": "Co", "url": "http://co.com"},
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

@pytest.mark.asyncio
async def test_arbeitnow_main_orchestration():
    """Test full orchestration for Arbeitnow."""
    mock_api_data = {
        "data": [
            {
                "slug": "python-dev",
                "title": "Senior Python Developer",
                "company_name": "Tech Corp",
                "description": "Django expert needed.",
                "url": "https://arbeitnow.com/python-dev"
            },
            {
                "slug": "hr-manager",
                "title": "HR Manager",
                "company_name": "Sales Corp",
                "description": "Recruitment role.",
                "url": "https://arbeitnow.com/hr"
            }
        ]
    }
    
    mock_ai_results = {
        "job_roles": [["Backend Dev"]],
        "tags": [["Python"]]
    }

    with patch("ingestion_module.hiring.arbeitnow.fetch.fetch_jobs", return_value=mock_api_data):
        with patch("ingestion_module.hiring.arbeitnow.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "Arbeitnow"
            assert len(results["title"]) == 1
            assert results["title"][0] == "Senior Python Developer"
            assert results["job_roles"][0] == ["Backend Dev"]
