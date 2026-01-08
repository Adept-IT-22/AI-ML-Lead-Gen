"""
Pytest test cases for Remotive Jobs module.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os


# Add Backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable BEFORE importing modules that might check it
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.remotive import fetch as fetch_mod

@pytest.mark.asyncio
async def test_main_success_remotive():
    """Test Remotive main success."""
    fake_jobs = {
        "jobs": [
            {
                "id": 1,
                "title": "Senior Python Developer",
                "url": "https://remotive.com/job/1",
                "category": "Software Development",
                "publication_date": "2026-01-06T10:00:00"
            },
            {
                "id": 2,
                "title": "Marketing Guru",
                "url": "https://remotive.com/job/2",
                "category": "Marketing",
                "publication_date": "2026-01-06T10:00:00"
            }
        ]
    }
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=fake_jobs)
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    extracted_data = {
        "article_id": ["1"],
        "article_link": ["https://remotive.com/job/1"],
        "title": ["Senior Python Developer"],
    }
    
    async def mock_finalize(data):
        return extracted_data

    with patch('ingestion_module.hiring.remotive.fetch.httpx.AsyncClient', return_value=mock_client):
        with patch('ingestion_module.hiring.remotive.fetch.finalize_ai_extraction', side_effect=mock_finalize):
            result = await fetch_mod.main()
            
            print(f"DEBUG: Result keys: {result.keys() if result else 'None'}")
            if result:
                print(f"DEBUG: Result link: {result.get('link')}")
                print(f"DEBUG: Result title: {result.get('title')}")
            
            assert result is not None
            assert result["source"] == "Remotive"
            assert len(result["link"]) == 1
            assert "https://remotive.com/job/1" in result["link"]

