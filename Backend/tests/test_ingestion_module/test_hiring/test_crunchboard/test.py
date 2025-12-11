import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add Backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ingestion_module.hiring.crunchboard import fetch


@pytest.mark.asyncio
async def test_collect_recent_job_urls(monkeypatch):
    """Test collecting job URLs from sitemap"""
    import asyncio
    semaphore = asyncio.Semaphore(3)
    
    # Mock the fetch functions
    async def mock_fetch_sitemap_index(sem):
        return ["https://example.com/sitemap1.xml"]
    
    async def mock_fetch_job_sitemap(url, sem):
        return [
            {"url": "https://example.com/job/1", "lastmod": "2025-11-30"},
            {"url": "https://example.com/job/2", "lastmod": "2025-11-15"},
        ]
    
    monkeypatch.setattr(fetch, "fetch_sitemap_index", mock_fetch_sitemap_index)
    monkeypatch.setattr(fetch, "fetch_job_sitemap", mock_fetch_job_sitemap)
    
    urls = await fetch.collect_recent_job_urls(semaphore)
    
    assert len(urls) == 2
    assert "https://example.com/job/1" in urls


def test_extract_job_data_with_json_ld():
    """Test extracting job data from HTML with JSON-LD"""
    html_content = '''
    <script type="application/ld+json">
    {
        "title": "Software Engineer",
        "hiringOrganization": {"name": "TechCorp"},
        "description": "<p>Great job opportunity</p>",
        "datePosted": "2025-11-30"
    }
    </script>
    '''
    
    result = fetch.extract_job_data(html_content, "https://example.com/job/1")
    
    assert result is not None
    assert result["title"] == "Software Engineer"
    assert result["company"] == "TechCorp"
    assert "Great job opportunity" in result["description"]


def test_extract_job_data_fallback_html():
    """Test extracting job data from HTML without JSON-LD"""
    html_content = '''
    <h1 class="u-textH2">Senior Developer</h1>
    <div class="text-primary text-large"><strong>AmazingCo</strong></div>
    <div class="job-body">
        <p>This is a great opportunity for a senior developer.</p>
    </div>
    '''
    
    result = fetch.extract_job_data(html_content, "https://example.com/job/2")
    
    assert result is not None
    assert result["title"] == "Senior Developer"
    assert result["company"] == "AmazingCo"
    assert "great opportunity" in result["description"]


@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    """Test main function with successful job extraction"""
    import asyncio
    
    # Mock collect_recent_job_urls
    async def mock_collect_urls(sem):
        return ["https://example.com/job/1"]
    
    # Mock fetch_job_pages
    async def mock_fetch_pages(urls, sem):
        return [{
            "title": "Test Job",
            "company": "TestCorp",
            "description": "Test description",
            "url": "https://example.com/job/1"
        }]
    
    # Mock finalize_ai_extraction
    async def mock_ai_extraction(data):
        return {
            "company_decision_makers": [["John Doe"]],
            "hiring_reasons": [["Expansion"]],
            "job_roles": [["Engineer"]],
            "tags": [["Python"]]
        }
    
    monkeypatch.setattr(fetch, "collect_recent_job_urls", mock_collect_urls)
    monkeypatch.setattr(fetch, "fetch_job_pages", mock_fetch_pages)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_extraction)
    
    # Mock fetch_with_scraper for warmup
    async def mock_fetch(url, **kwargs):
        return "<html></html>"
    monkeypatch.setattr(fetch, "fetch_with_scraper", mock_fetch)
    
    result = await fetch.main()
    
    assert result is not None
    assert result["source"] == "crunchboard"
    assert result["type"] == "hiring"
    assert len(result["link"]) == 1


@pytest.mark.asyncio
async def test_main_no_jobs(monkeypatch):
    """Test main function when no jobs are found"""
    import asyncio
    
    async def mock_collect_urls(sem):
        return []
    
    monkeypatch.setattr(fetch, "collect_recent_job_urls", mock_collect_urls)
    
    result = await fetch.main()
    
    assert result is None


def test_is_within_last_60_days():
    """Test date filtering function"""
    from datetime import datetime, timedelta
    
    # Recent date
    recent = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    assert fetch.is_within_last_60_days(recent) == True
    
    # Old date
    old = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert fetch.is_within_last_60_days(old) == False
    
    # None
    assert fetch.is_within_last_60_days(None) == False
