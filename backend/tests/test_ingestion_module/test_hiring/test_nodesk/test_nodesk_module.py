import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from Backend.ingestion_module.hiring.nodesk.fetch import fetch_sitemap_urls, fetch_job_details, main

@pytest.mark.asyncio
async def test_fetch_sitemap_urls():
    mock_response = MagicMock()
    mock_response.text = """
    <urlset>
        <url><loc>https://nodesk.co/remote-jobs/dev-1/</loc></url>
        <url><loc>https://nodesk.co/remote-jobs/dev-2/</loc></url>
        <url><loc>https://nodesk.co/other/</loc></url>
    </urlset>
    """
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    urls = await fetch_sitemap_urls(mock_client)
    assert len(urls) == 2
    assert "https://nodesk.co/remote-jobs/dev-1/" in urls
    assert "https://nodesk.co/other/" not in urls

@pytest.mark.asyncio
async def test_fetch_job_details():
    mock_html = """
    <html>
        <body>
            <h1>Senior Python Developer</h1>
            <meta property="og:description" content="Job opportunity at Acme Corp for a Senior Python Developer">
            <main>We need someone who knows Python.</main>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    url = "https://nodesk.co/remote-jobs/senior-python-developer/"
    job = await fetch_job_details(mock_client, url)

    assert job["title"] == "Senior Python Developer"
    assert job["company"] == "Acme Corp"
    assert "knows Python" in job["description"]

@pytest.mark.asyncio
@patch("Backend.ingestion_module.hiring.nodesk.fetch.fetch_sitemap_urls")
@patch("Backend.ingestion_module.hiring.nodesk.fetch.fetch_job_details")
@patch("Backend.ingestion_module.hiring.nodesk.fetch.finalize_ai_extraction")
@patch("Backend.ingestion_module.hiring.nodesk.fetch.software_dev_keywords", ["developer"])
async def test_main_orchestration(mock_ai, mock_details, mock_sitemap):
    mock_sitemap.return_value = ["https://nodesk.co/remote-jobs/developer/"]
    mock_details.return_value = {
        "id": "abc",
        "title": "Developer",
        "company": "Scale",
        "description": "desc",
        "url": "https://nodesk.co/remote-jobs/developer/",
        "date": "2024-01-01"
    }
    mock_ai.return_value = {
        "job_roles": [["Full Stack Developer"]]
    }

    results = await main()
    assert len(results["title"]) == 1
    assert results["source"] == "NoDesk"
    assert results["job_roles"] == [["Full Stack Developer"]]
