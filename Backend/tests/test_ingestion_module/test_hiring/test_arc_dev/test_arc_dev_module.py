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

from ingestion_module.hiring.arc_dev.fetch import fetch_job_urls, fetch_job_details, main

@pytest.mark.asyncio
async def test_fetch_job_urls():
    """Test extracting job URLs from main page."""
    mock_html = """
    <html>
        <body>
            <a href="/remote-jobs/j/company-job-1">Job 1</a>
            <a href="/remote-jobs/j/company-job-2">Job 2</a>
            <a href="/remote-jobs/python">Category</a>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    
    urls = await fetch_job_urls(mock_client)
    assert len(urls) == 2
    assert "https://arc.dev/remote-jobs/j/company-job-1" in urls

@pytest.mark.asyncio
async def test_fetch_job_details():
    """Test extracting detailed job data."""
    mock_html = """
    <html>
        <head>
            <meta property="og:description" content="Job opportunity at Acme Corp for a Senior Developer">
        </head>
        <body>
            <h1><span>Senior Developer</span></h1>
            <main>We need experts.</main>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    
    url = "https://arc.dev/remote-jobs/j/acme-senior-developer-123"
    job = await fetch_job_details(mock_client, url)
    
    assert job["id"] == "123"
    assert job["title"] == "Senior Developer"
    assert job["company"] == "Acme Corp"
    assert "experts" in job["description"]

@pytest.mark.asyncio
async def test_arc_dev_main_orchestration():
    """Test main orchestration and filtering."""
    mock_urls = ["https://arc.dev/remote-jobs/j/company-python-developer-1"]
    mock_job = {
        "id": "1",
        "title": "Python Developer",
        "company": "Tech",
        "description": "desc",
        "url": mock_urls[0],
        "date": "2026-01-08"
    }
    
    mock_ai_results = {
        "job_roles": [["Full Stack Developer"]],
        "tags": [["Python"]]
    }

    with patch("ingestion_module.hiring.arc_dev.fetch.fetch_job_urls", return_value=mock_urls):
        with patch("ingestion_module.hiring.arc_dev.fetch.fetch_job_details", return_value=mock_job):
            with patch("ingestion_module.hiring.arc_dev.fetch.finalize_ai_extraction", return_value=mock_ai_results):
                results = await main()
                
                assert results is not None
                assert results["source"] == "Arc.dev"
                assert len(results["title"]) == 1
                assert results["title"][0] == "Python Developer"
                assert results["job_roles"][0] == ["Full Stack Developer"]
