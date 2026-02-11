import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from backend.ingestion_module.hiring.working_nomads.fetch import fetch_sitemap_urls, fetch_job_details, main

@pytest.mark.asyncio
async def test_fetch_sitemap_urls():
    mock_response = MagicMock()
    mock_response.text = """
    <urlset>
        <url><loc>https://www.workingnomads.com/jobs/dev-1</loc></url>
        <url><loc>https://www.workingnomads.com/jobs/dev-2</loc></url>
        <url><loc>https://www.workingnomads.com/jobs</loc></url>
    </urlset>
    """
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    urls = await fetch_sitemap_urls(mock_client)
    assert len(urls) == 2
    assert "https://www.workingnomads.com/jobs/dev-1" in urls
    assert "https://www.workingnomads.com/jobs" not in urls

@pytest.mark.asyncio
async def test_fetch_job_details():
    mock_html = """
    <html>
        <head>
            <title>Senior Developer at AwesomeCo | Working Nomads</title>
        </head>
        <body>
            <h1 class="job-title">Senior Developer at AwesomeCo</h1>
            <div class="description">We are looking for a dev.</div>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    url = "https://www.workingnomads.com/jobs/senior-developer-awesomeco"
    job = await fetch_job_details(mock_client, url)

    assert job["title"] == "Senior Developer"
    assert job["company"] == "AwesomeCo"
    assert "looking for a dev" in job["description"]

@pytest.mark.asyncio
@patch("backend.ingestion_module.hiring.working_nomads.fetch.fetch_sitemap_urls")
@patch("backend.ingestion_module.hiring.working_nomads.fetch.fetch_job_details")
@patch("backend.ingestion_module.hiring.working_nomads.fetch.finalize_ai_extraction")
@patch("backend.ingestion_module.hiring.working_nomads.fetch.software_dev_keywords", ["python", "engineer"])
async def test_main_orchestration(mock_ai, mock_details, mock_sitemap):
    # Mock sitemap URLs
    mock_sitemap.return_value = [
        "https://www.workingnomads.com/jobs/python-developer",
        "https://www.workingnomads.com/jobs/marketing-manager"
    ]
    
    # Mock job details
    mock_details.return_value = {
        "id": "123",
        "title": "Python Developer",
        "company": "TechCorp",
        "description": "Python job",
        "url": "https://www.workingnomads.com/jobs/python-developer",
        "source": "Working Nomads",
        "date": "2024-01-01"
    }

    # Mock AI extraction result
    mock_ai.return_value = {
        "job_roles": [["Python Dev"]],
        "hiring_reasons": [["Expansion"]]
    }

    # Trigger wait time for mock
    results = await main()

    # result count should be 1 because marketing-manager doesn't match keys
    assert len(results["title"]) == 1 
    assert results["source"] == "working_nomads"
    assert results["job_roles"] == [["Python Dev"]]
    assert results["link"][0] == "https://www.workingnomads.com/jobs/python-developer"
