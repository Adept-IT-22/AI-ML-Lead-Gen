import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from backend.ingestion_module.hiring.jobspresso.fetch import fetch_sitemap_urls, fetch_job_details, main

@pytest.mark.asyncio
async def test_fetch_sitemap_urls():
    mock_response = MagicMock()
    mock_response.text = """
    <urlset>
        <url><loc>https://jobspresso.co/job/dev-1/</loc></url>
        <url><loc>https://jobspresso.co/job/dev-2/</loc></url>
        <url><loc>https://jobspresso.co/other/</loc></url>
    </urlset>
    """
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    urls = await fetch_sitemap_urls(mock_client)
    assert len(urls) == 2
    assert "https://jobspresso.co/job/dev-1/" in urls
    assert "https://jobspresso.co/other/" not in urls

@pytest.mark.asyncio
async def test_fetch_job_details():
    mock_html = """
    <html>
        <body>
            <h1 class="job_title">Senior Java Engineer</h1>
            <div class="company"><strong>Tech Solutions</strong></div>
            <div class="job_description">Build great things.</div>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    url = "https://jobspresso.co/job/senior-java-engineer/"
    job = await fetch_job_details(mock_client, url)

    assert job["title"] == "Senior Java Engineer"
    assert job["company"] == "Tech Solutions"
    assert "Build great things" in job["description"]

@pytest.mark.asyncio
@patch("backend.ingestion_module.hiring.jobspresso.fetch.fetch_sitemap_urls")
@patch("backend.ingestion_module.hiring.jobspresso.fetch.fetch_job_details")
@patch("backend.ingestion_module.hiring.jobspresso.fetch.finalize_ai_extraction")
@patch("backend.ingestion_module.hiring.jobspresso.fetch.software_dev_keywords", ["engineer"])
async def test_main_orchestration(mock_ai, mock_details, mock_sitemap):
    mock_sitemap.return_value = ["https://jobspresso.co/job/software-engineer/"]
    mock_details.return_value = {
        "id": "abc",
        "title": "Software Engineer",
        "company": "Scale",
        "description": "desc",
        "url": "https://jobspresso.co/job/software-engineer/",
        "date": ""
    }
    mock_ai.return_value = {
        "job_roles": [["Frontend Engineer"]]
    }

    results = await main()
    assert len(results["title"]) == 1
    assert results["source"] == "Jobspresso"
    assert results["job_roles"] == [["Frontend Engineer"]]
