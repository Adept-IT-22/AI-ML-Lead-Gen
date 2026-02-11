import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.remote_frontend_jobs.fetch import main

@pytest.mark.asyncio
async def test_rfj_main_orchestration():
    """Test full orchestration for Remote Frontend Jobs."""
    
    # Mock Sitemap
    mock_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://www.remotefrontendjobs.com/job-1-react</loc>
            <lastmod>2026-01-12T10:00:00.000Z</lastmod>
        </url>
        <url>
            <loc>https://www.remotefrontendjobs.com/remote-frontend-jobs</loc>
            <lastmod>2026-01-01T10:00:00.000Z</lastmod>
        </url>
    </urlset>
    """
    
    # Mock Job Page HTML
    mock_job_page = "<html><title>React Developer</title><body>Desc</body></html>"

    async def mock_fetch(client, url):
        if "sitemap" in url:
            return mock_sitemap
        return mock_job_page

    mock_ai = {
        "company_name": ["React Co"],
        "tags": [["React"]]
    }

    with patch("ingestion_module.hiring.remote_frontend_jobs.fetch.fetch_url_text", side_effect=mock_fetch):
        with patch("ingestion_module.hiring.remote_frontend_jobs.fetch.finalize_ai_extraction", return_value=mock_ai):
            results = await main()
            
            assert results["source"] == "Remote Frontend Jobs"
            # Should filter out "remote-frontend-jobs" static page
            assert len(results["title"]) == 1
            assert results["title"][0] == "React Developer"
            assert results["link"][0] == "https://www.remotefrontendjobs.com/job-1-react"
