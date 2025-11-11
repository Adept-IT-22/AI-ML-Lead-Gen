"""
Pytest test cases for Stack Overflow Jobs module.
Tests Selenium integration, HTML parsing, date filtering, and job extraction.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
from ingestion_module.hiring.stackoverflow_jobs import fetch as fetch_mod


@pytest_asyncio.fixture
def mock_client():
    """Create a mock httpx.AsyncClient."""
    return MagicMock()


@pytest.mark.asyncio
async def test_parse_posted_date_recent():
    """Test that recent dates are parsed correctly."""
    # Test "Posted 5 days ago"
    date_str = "Posted 5 days ago"
    result = fetch_mod.parse_posted_date(date_str)
    assert result is not None
    assert isinstance(result, datetime)
    # Should be approximately 5 days ago
    days_diff = (datetime.now() - result).days
    assert 4 <= days_diff <= 6


@pytest.mark.asyncio
async def test_parse_posted_date_old():
    """Test that old dates are parsed correctly."""
    # Test "Posted 3 months ago"
    date_str = "Posted 3 months ago"
    result = fetch_mod.parse_posted_date(date_str)
    assert result is not None
    assert isinstance(result, datetime)
    # Should be approximately 90 days ago
    days_diff = (datetime.now() - result).days
    assert 85 <= days_diff <= 95


@pytest.mark.asyncio
async def test_parse_posted_date_invalid():
    """Test that invalid dates return None."""
    result = fetch_mod.parse_posted_date("Invalid date")
    assert result is None


@pytest.mark.asyncio
async def test_is_within_last_two_months_recent():
    """Test that recent dates (within 2 months) return True."""
    recent_date = datetime.now() - timedelta(days=30)
    result = fetch_mod.is_within_last_two_months(recent_date)
    assert result


@pytest.mark.asyncio
async def test_is_within_last_two_months_old():
    """Test that old dates (beyond 2 months) return False."""
    old_date = datetime.now() - timedelta(days=90)
    result = fetch_mod.is_within_last_two_months(old_date)
    assert not result


@pytest.mark.asyncio
async def test_is_within_last_two_months_none():
    """Test that None date returns False."""
    result = fetch_mod.is_within_last_two_months(None)
    assert not result


@pytest.mark.asyncio
async def test_parse_job_listings_extracts_jobs():
    """Test that job listings are parsed correctly from HTML."""
    html_content = """
    <ul id="job-list">
        <li class="chakra-list__item">
            <div data-jobkey="12345" class="css-2wbm9t">
                <div class="css-1pip4vl">
                    <div class="css-jsttvt">
                        <h2 class="css-1in8x96">Software Engineer</h2>
                        <p class="css-1pnk0le">TechCorp</p>
                        <p class="css-u7ev33">San Francisco</p>
                        <p class="css-13x1vyp">Posted 5 days ago</p>
                    </div>
                </div>
            </div>
        </li>
    </ul>
    """
    
    jobs = fetch_mod.parse_job_listings(html_content)
    
    assert len(jobs) == 1
    assert jobs[0]["id"] == "12345"
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[0]["company"] == "TechCorp"
    assert jobs[0]["location"] == "San Francisco"


@pytest.mark.asyncio
async def test_parse_job_listings_filters_old_jobs():
    """Test that old jobs (beyond 2 months) are filtered out."""
    html_content = """
    <ul id="job-list">
        <li class="chakra-list__item">
            <div data-jobkey="12345" class="css-2wbm9t">
                <div class="css-1pip4vl">
                    <div class="css-jsttvt">
                        <h2 class="css-1in8x96">Software Engineer</h2>
                        <p class="css-1pnk0le">TechCorp</p>
                        <p class="css-u7ev33">San Francisco</p>
                        <p class="css-13x1vyp">Posted 6 months ago</p>
                    </div>
                </div>
            </div>
        </li>
    </ul>
    """
    
    jobs = fetch_mod.parse_job_listings(html_content)
    
    # Should be filtered out because it's older than 2 months
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_extract_job_postings_formats_correctly():
    """Test that job postings are formatted correctly for AI extraction."""
    jobs = [
        {
            "id": "12345",
            "url": "https://stackoverflowjobs.com/?co=US&jk=12345",
            "title": "Software Engineer",
            "company": "TechCorp",
            "location": "San Francisco"
        },
        {
            "id": "67890",
            "url": "https://stackoverflowjobs.com/?co=US&jk=67890",
            "title": "Data Scientist",
            "company": "DataCorp",
            "location": "New York"
        }
    ]
    
    job_postings = fetch_mod.extract_job_postings(jobs)
    
    assert len(job_postings["ids"]) == 2
    assert len(job_postings["urls"]) == 2
    assert len(job_postings["titles"]) == 2
    assert "12345" in job_postings["ids"]
    assert "67890" in job_postings["ids"]
    assert "Software Engineer | TechCorp | San Francisco" in job_postings["titles"]


@pytest.mark.asyncio
async def test_fetch_page_with_selenium_success(monkeypatch):
    """Test that Selenium page fetching works correctly."""
    mock_driver = MagicMock()
    mock_driver.page_source = "<html><body><div id='job-list'>Jobs</div></body></html>"
    mock_driver.execute_cdp_cmd = MagicMock()
    mock_driver.get = MagicMock()
    mock_driver.quit = MagicMock()
    
    def mock_create_driver(headless=True):
        return mock_driver
    
    with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.create_driver', side_effect=mock_create_driver):
        with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.WebDriverWait') as mock_wait:
            with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.time.sleep'):
                mock_wait_instance = MagicMock()
                mock_wait_instance.until = MagicMock()
                mock_wait.return_value = mock_wait_instance
                result = await fetch_mod.fetch_page_with_selenium("https://stackoverflowjobs.com/?co=US", wait_time=10)
                
                assert result is not None
                assert "job-list" in result
                mock_driver.quit.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_job_listings_page_success(monkeypatch):
    """Test that job listings page is fetched successfully."""
    # HTML must be at least 1000 characters to pass the length check
    mock_html = "<html><body><ul id='job-list'>" + "".join([f"<li>Job {i}</li>" for i in range(100)]) + "</ul></body></html>"
    
    async def mock_fetch_page(url, wait_time):
        return mock_html
    
    with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.fetch_page_with_selenium', side_effect=mock_fetch_page):
        result = await fetch_mod.fetch_job_listings_page(page=1, country="US")
        
        assert result is not None
        assert result == mock_html


@pytest.mark.asyncio
async def test_main_success_with_mocked_data(monkeypatch):
    """Test the main function with mocked data."""
    # Mock HTML content with jobs
    mock_html = """
    <ul id="job-list">
        <li class="chakra-list__item">
            <div data-jobkey="12345" class="css-2wbm9t">
                <div class="css-1pip4vl">
                    <div class="css-jsttvt">
                        <h2 class="css-1in8x96">Software Engineer</h2>
                        <p class="css-1pnk0le">TechCorp</p>
                        <p class="css-u7ev33">San Francisco</p>
                        <p class="css-13x1vyp">Posted 5 days ago</p>
                    </div>
                </div>
            </div>
        </li>
    </ul>
    """
    
    # Mock extracted data from AI
    extracted_data = {
        "article_id": ["12345"],
        "article_title": ["Software Engineer at TechCorp"],
        "company_name": ["TechCorp"],
        "job_roles": [["software engineer"]],
        "company_city": ["San Francisco"],
        "company_country": ["USA"]
    }
    
    async def mock_fetch_page(page, country):
        return mock_html
    
    async def mock_finalize_ai_extraction(data):
        return extracted_data
    
    with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.fetch_job_listings_page', side_effect=mock_fetch_page):
        with patch('ingestion_module.ai_extraction.extract_hiring_content.finalize_ai_extraction', new=mock_finalize_ai_extraction):
            result = await fetch_mod.main()
            
            assert result is not None
            assert result["source"] == "StackOverflowJobs"
            assert "TechCorp" in result["company_name"]


@pytest.mark.asyncio
async def test_main_no_jobs_found(monkeypatch):
    """Test main function when no jobs are found."""
    async def mock_fetch_page(page, country):
        if page == 1:
            return None  # No HTML content on first page
        return None
    
    with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.fetch_job_listings_page', side_effect=mock_fetch_page):
        result = await fetch_mod.main()
        
        # main() returns {} when no jobs found, or None if there's an exception
        assert result == {} or result is None


@pytest.mark.asyncio
async def test_main_empty_html(monkeypatch):
    """Test main function when HTML is empty or too short."""
    async def mock_fetch_page(page, country):
        if page == 1:
            return "<html></html>"  # Too short
        return None
    
    with patch('ingestion_module.hiring.stackoverflow_jobs.fetch.fetch_job_listings_page', side_effect=mock_fetch_page):
        result = await fetch_mod.main()
        
        # main() returns {} when no jobs found, or None if there's an exception
        assert result == {} or result is None

