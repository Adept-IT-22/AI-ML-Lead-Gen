import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.eu_startups import fetch

# Helper class for mocking httpx responses
class MockResponse:
    def __init__(self, content, status_code=200, url="", headers=None):
        self.content = content.encode('utf-8')
        self.text = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {"Content-Type": "application/xml"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")

@pytest.mark.asyncio
async def test_fetch_eu_startups_data_happy_path(monkeypatch):
    """
    Tests the two-level sitemap filtering for EU-Startups.
    1. Filters child sitemaps by name ('post-sitemap') and date.
    2. Filters articles within those sitemaps by date and keywords.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_date_str = now.isoformat()
    slightly_less_recent_date_str = (now - datetime.timedelta(days=10)).isoformat()
    old_date_str = (now - datetime.timedelta(days=90)).isoformat()

    # Mock sitemap index file (level 1)
    sitemap_index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- Case 1: Should be fetched (recent post-sitemap) -->
        <sitemap>
            <loc>https://www.eu-startups.com/post-sitemap1.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
        <!-- Case 2: Should be IGNORED (old post-sitemap) -->
        <sitemap>
            <loc>https://www.eu-startups.com/post-sitemap2.xml</loc>
            <lastmod>{old_date_str}</lastmod>
        </sitemap>
        <!-- Case 3: Should be IGNORED (not a 'post-sitemap') -->
        <sitemap>
            <loc>https://www.eu-startups.com/page-sitemap.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
    </sitemapindex>
    """

    # Mock child sitemap with article links (level 2)
    child_sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- Article 1: Should be selected (recent, has keywords) -->
        <url>
            <loc>https://www.eu-startups.com/2024/01/german-ai-startup-secures-funding/</loc>
            <lastmod>{recent_date_str}</lastmod>
        </url>
        <!-- Article 2: Should be IGNORED (old date) -->
        <url>
            <loc>https://www.eu-startups.com/2023/10/old-story-about-ai-funding/</loc>
            <lastmod>{old_date_str}</lastmod>
        </url>
        <!-- Article 3: Should be IGNORED (no funding keyword) -->
        <url>
            <loc>https://www.eu-startups.com/2024/01/new-ai-technology-unveiled/</loc>
            <lastmod>{recent_date_str}</lastmod>
        </url>
        <!-- Article 4: Should be selected (recent, has keywords) -->
        <url>
            <loc>https://www.eu-startups.com/2024/01/machine-learning-firm-raises-capital/</loc>
            <lastmod>{slightly_less_recent_date_str}</lastmod>
        </url>
    </urlset>
    """

    # Mock fetch_with_retries to handle the two-level fetch
    async def mock_fetch(client, url):
        if url == "https://www.eu-startups.com/sitemap_index.xml":
            return MockResponse(sitemap_index_xml)
        elif url == "https://www.eu-startups.com/post-sitemap1.xml":
            return MockResponse(child_sitemap_xml)
        # Any other URL is unexpected and should fail
        return MockResponse("", status_code=404)

    monkeypatch.setattr(fetch, "fetch_with_retries", mock_fetch)

    # Mock extract_paragraphs to avoid real network calls
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    # Run the function under test
    results = await fetch.fetch_eu_startups_data()

    # Assertions
    expected_urls = [
        "https://www.eu-startups.com/2024/01/german-ai-startup-secures-funding/",
        "https://www.eu-startups.com/2024/01/machine-learning-firm-raises-capital/"
    ]
    assert len(results["urls"]) == 2
    assert all(url in results["urls"] for url in expected_urls)
    assert "https://www.eu-startups.com/2024/01/new-ai-technology-unveiled/" not in results["urls"]
    assert "Paragraph from https://www.eu-startups.com/2024/01/german-ai-startup-secures-funding/" in results["paragraphs"]

@pytest.mark.asyncio
async def test_extract_paragraphs_from_eu_startup_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from EU-Startups' specific HTML structure.
    """
    html_content = """
    <html><body>
        <div class="tdb-block-inner">
            <p>This is the first paragraph.</p>
            <p>This is the second, with <strong>bold text</strong>.</p>
            <p>  </p> <!-- This empty one should be ignored -->
        </div>
        <div class="another-div"><p>This paragraph should NOT be extracted.</p></div>
    </body></html>
    """
    test_url = "https://www.eu-startups.com/fake-article"
    
    mock_html_response = MockResponse(html_content, 200, url=test_url, headers={"Content-Type": "text/html"})
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_html_response

    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    assert url == test_url
    assert len(paragraphs) == 2
    assert paragraphs[0] == "This is the first paragraph."
    assert paragraphs[1] == "This is the second, with bold text."

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    fake_fetched_data = {
        "urls": ["https://www.eu-startups.com/2024/01/german-ai-startup-secures-funding/"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_eu_startups_data", AsyncMock(return_value=fake_fetched_data))

    fake_ai_result = {
        "company_name": ["EU-AI GmbH"],
        "amount_raised": ["€5M"],
        "investors": ["EU Ventures"],
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    assert result is not None
    assert result["source"] == ["eu-startups.com"]
    assert result["company_name"] == ["EU-AI GmbH"]
    assert result["amount_raised"] == ["€5M"]
    assert result["link"] == ["https://www.eu-startups.com/2024/01/german-ai-startup-secures-funding/"]