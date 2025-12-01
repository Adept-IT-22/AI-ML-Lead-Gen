import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add Backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ingestion_module.hiring.stackoverflow_jobs import fetch


def test_parse_job_card_success():
    """Test successful parsing of a job card"""
    mock_job_card = Mock()
    
    mock_title_elem = Mock()
    mock_title_elem.text = "Senior Software Engineer"
    
    mock_company_elem = Mock()
    mock_company_elem.text = "TechCorp"
    
    mock_location_elem = Mock()
    mock_location_elem.text = "Berlin, Germany"
    
    mock_link_elem = Mock()
    mock_link_elem.get_attribute.return_value = "job_123abc"
    
    mock_snippet_elem = Mock()
    mock_snippet_elem.text = "Great opportunity"
    
    mock_date_elem = Mock()
    mock_date_elem.text = "2 days ago"
    
    def find_element_side_effect(by, selector):
        if "jobTitle span" in selector:
            return mock_title_elem
        elif "company-name" in selector:
            return mock_company_elem
        elif "text-location" in selector:
            return mock_location_elem
        elif "jobTitle a" in selector:
            return mock_link_elem
        return Mock()
    
    def find_elements_side_effect(by, selector):
        if "job-snippet" in selector:
            return [mock_snippet_elem]
        elif "myJobsStateDate" in selector:
            return [mock_date_elem]
        return []
    
    mock_job_card.find_element.side_effect = find_element_side_effect
    mock_job_card.find_elements.side_effect = find_elements_side_effect
    
    result = fetch.parse_job_card(mock_job_card)
    
    assert result is not None
    assert result["title"] == "Senior Software Engineer"
    assert result["company"] == "TechCorp"
    assert "123abc" in result["url"]


def test_parse_job_card_error():
    """Test error handling in parse_job_card"""
    mock_job_card = Mock()
    mock_job_card.find_element.side_effect = Exception("Error")
    
    result = fetch.parse_job_card(mock_job_card)
    assert result is None


@pytest.mark.asyncio
async def test_main_no_jobs(monkeypatch):
    """Test main with no jobs"""
    monkeypatch.setattr(fetch, "scrape_indeed_jobs", lambda region, max_pages: [])
    result = await fetch.main()
    assert result is None


@pytest.mark.asyncio
async def test_main_with_jobs(monkeypatch):
    """Test main with jobs"""
    mock_jobs = [{
        "id": "job_123",
        "title": "Software Engineer",
        "company": "TechCorp",
        "location": "Berlin, Germany",
        "url": "https://example.com/job/123",
        "snippet": "Great job",
        "posted_date": "2 days ago"
    }]
    
    monkeypatch.setattr(fetch, "scrape_indeed_jobs", 
                       lambda region, max_pages: mock_jobs if region == "Germany" else [])
    
    async def mock_llm(data):
        return {
            "company_decision_makers": [["John Doe"]],
            "hiring_reasons": [["Expansion"]],
            "job_roles": [["Engineer"]],
            "tags": [["Python"]]
        }
    
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_llm)
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "Indeed (Stack Overflow Jobs)"
    assert "Software Engineer" in result["title"]
