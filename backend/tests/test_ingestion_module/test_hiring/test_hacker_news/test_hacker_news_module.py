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

from ingestion_module.hiring.hacker_news.fetch import dict_of_lists, main

def test_dict_of_lists_filtering():
    """Test that jobs are correctly filtered by software dev keywords."""
    raw_jobs = [
        {"id": 1, "title": "Hiring: Senior Python Engineer", "url": "https://company.com/python", "by": "user1", "time": 12345},
        {"id": 2, "title": "Looking for Head Chef", "url": "https://restaurant.com/chef", "by": "user2", "time": 12346},
        {"id": 3, "title": "We are hiring!", "description": "Needs React Native", "url": "https://company.com/react", "by": "user3", "time": 12347}
    ]
    
    # Needs a mock software_dev_keywords if not importing correctly, but assuming fetch imports it ok
    # The actual implementation imports it. 
    # Python is in keywords, Marketing is not. React should be (if in list).
    
    result = dict_of_lists(raw_jobs)
    
    # Check that the Python job is definitely there
    assert "Hiring: Senior Python Engineer" in result["title"]
    assert len(result["id"]) >= 1

@pytest.mark.asyncio
async def test_hn_main_orchestration():
    """Test full orchestration for Hacker News."""
    mock_ids = [101, 102]
    mock_details = [
        {"id": 101, "title": "Remote Backend Dev (Python)", "url": "http://a.com", "by": "pg", "time": 1000},
        {"id": 102, "title": "Sales Lead", "url": "http://b.com", "by": "ama", "time": 1001}
    ]
    
    mock_ai_results = {
        "company_name": ["YCombinator"],
        "job_roles": [["Backend"]],
        "tags": [["Python"]]
    }

    # Mock fetch_hackernews_jobs
    with patch("ingestion_module.hiring.hacker_news.fetch.fetch_hackernews_jobs", return_value=mock_ids):
        # Mock get_all_job_details
        with patch("ingestion_module.hiring.hacker_news.fetch.get_all_job_details", return_value=mock_details):
             # Mock AI
            with patch("ingestion_module.hiring.hacker_news.fetch.finalize_ai_extraction", return_value=mock_ai_results):
                results = await main()
                
                assert results is not None
                assert results["source"] == "HackerNews"
                # Sales Lead should be filtered out
                assert len(results["title"]) == 1
                assert "Python" in results["title"][0]
                assert results["company_decision_makers"][0] == ["pg"]
                assert results["company_name"][0] == "YCombinator"
