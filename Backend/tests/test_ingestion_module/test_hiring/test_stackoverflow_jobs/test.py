import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add Backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ingestion_module.hiring.stackoverflow_jobs import fetch


def test_parse_job_card_success():
    """Test successful parsing of a job card"""
    # Mock job card element
    mock_job_card = Mock()
    
    # Mock title
    mock_title_elem = Mock()
    mock_title_elem.text = "Senior Software Engineer"
    
    # Mock company
    mock_company_elem = Mock()
    mock_company_elem.text = "TechCorp"
    
    # Mock location
    mock_location_elem = Mock()
    mock_location_elem.text = "Berlin, Germany"
    
    # Mock link
    mock_link_elem = Mock()
    mock_link_elem.get_attribute.return_value = "job_123abc"
    
    # Mock snippet
    mock_snippet_elem = Mock()
    mock_snippet_elem.text = "Great opportunity for a senior dev"
    
    # Mock date
    mock_date_elem = Mock()
    mock_date_elem.text = "Posted 2 days ago"
    
    # Setup find_element returns
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
    
    # Setup find_elements returns
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
    assert result["location"] == "Berlin, Germany"
    assert "123abc" in result["url"]


def test_parse_job_card_error_handling():
    """Test error handling in parse_job_card"""
    # Mock job card that raises exception
    mock_job_card = Mock()
    mock_job_card.find_element.side_effect = Exception("Element not found")
    
    result = fetch.parse_job_card(mock_job_card)
    
    assert result is None


@pytest.mark.asyncio
async def test_main_no_jobs(monkeypatch):
    """Test main when no jobs are found"""
    # Mock scrape_indeed_jobs to return empty list
    monkeypatch.setattr(fetch, "scrape_indeed_jobs", lambda region, max_pages: [])
    
    result = await fetch.main()
    
    assert result is None


@pytest.mark.asyncio
async def test_main_with_jobs(monkeypatch):
    """Test main with successful job scraping"""
    # Mock scrape functions
    mock_jobs = [
        {
            "id": "job_123",
            "title": "Software Engineer",
            "company": "TechCorp",
            "location": "Berlin, Germany",
            "url": "https://example.com/job/123",
            "snippet": "Great job",
            "posted_date": "2 days ago"
        }
    ]
    
    monkeypatch.setattr(fetch, "scrape_indeed_jobs", lambda region, max_pages: mock_jobs if region == "Germany" else [])
    
    # Mock LLM extraction
    mock_extracted = {
        "company_decision_makers": [["John Doe"]],
        "hiring_reasons": [["Team expansion"]],
        "job_roles": [["Software Engineer"]],
        "tags": [["Python", "AWS"]]
    }
    monkeypatch.setattr(fetch, "finalize_ai_extraction", lambda x: mock_extracted)
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "Indeed (Stack Overflow Jobs)"
    assert len(result["title"]) >= 1
    assert "Software Engineer" in result["title"]


def test_setup_driver():
    """Test driver setup returns webdriver"""
    with patch('fetch.ChromeDriverManager') as mock_cdm, \
         patch('fetch.webdriver.Chrome') as mock_chrome:
        
        mock_cdm.return_value.install.return_value = "/path/to/chromedriver"
        mock_chrome.return_value = Mock()
        
        driver = fetch.setup_driver()
        
        assert driver is not None
