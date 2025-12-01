import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.american_bazaar_online import fetch

# Helper class for mocking cloudscraper responses
class MockResponse:
    def __init__(self, content, status_code=200, url=""):
        self.content = content.encode('utf-8')
        self.text = content
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")

@pytest.mark.asyncio
async def test_fetch_american_bazaar_data_happy_path(monkeypatch, caplog):
    """
    Tests the two-level sitemap filtering for americanbazaaronline.com.
    1. Finds the latest sitemap using date and a number tie-breaker.
    2. Filters articles within that sitemap by date and keywords.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_date_str = now.isoformat()
    slightly_older_date_str = (now - datetime.timedelta(days=1)).isoformat()
    old_date_str = (now - datetime.timedelta(days=90)).isoformat()

    # Mock sitemap index file (level 1)
    sitemap_index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- Case 1: Should be chosen (recent date, higher number) -->
        <sitemap>
            <loc>https://americanbazaaronline.com/post-sitemap22.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
        <!-- Case 2: Should be IGNORED (same recent date, lower number) -->
        <sitemap>
            <loc>https://americanbazaaronline.com/post-sitemap21.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
        <!-- Case 3: Should be IGNORED (older date) -->
        <sitemap>
            <loc>https://americanbazaaronline.com/post-sitemap20.xml</loc>
            <lastmod>{slightly_older_date_str}</lastmod>
        </sitemap>
        <!-- Case 4: Should be IGNORED (not a 'post-sitemap') -->
        <sitemap>
            <loc>https://americanbazaaronline.com/page-sitemap.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
        <!-- Case 5: Should be IGNORED (same recent date, lower number than 22) -->
        <sitemap>
            <loc>https://americanbazaaronline.com/post-sitemap.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
    </sitemapindex>
    """

    # Mock child sitemap with article links (level 2)
    child_sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- Article 1: Should be selected (recent, has keywords) -->
        <url>
            <loc>https://americanbazaaronline.com/2024/05/23/indian-american-led-ai-startup-secures-funding/</loc>
            <lastmod>{recent_date_str}</lastmod>
        </url>
        <!-- Article 2: Should be IGNORED (old date) -->
        <url>
            <loc>https://americanbazaaronline.com/2023/01/01/old-story-about-ai-funding/</loc>
            <lastmod>{old_date_str}</lastmod>
        </url>
        <!-- Article 3: Should be IGNORED (no funding keyword) -->
        <url>
            <loc>https://americanbazaaronline.com/2024/05/22/new-ai-technology-unveiled/</loc>
            <lastmod>{recent_date_str}</lastmod>
        </url>
    </urlset>
    """

    # Mock fetch_with_cloudscraper to handle the two-level fetch
    async def mock_fetch(client, url):
        if url == "https://americanbazaaronline.com/sitemap_index.xml":
            return MockResponse(sitemap_index_xml)
        elif url == "https://americanbazaaronline.com/post-sitemap22.xml":
            return MockResponse(child_sitemap_xml)
        return MockResponse("", status_code=404)

    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)

    # Mock extract_paragraphs to avoid real network calls
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    caplog.set_level("INFO")
    results = await fetch.fetch_american_bazaar_data()

    # Assertions
    assert "Processing latest sitemap: https://americanbazaaronline.com/post-sitemap22.xml" in caplog.text
    assert len(results["urls"]) == 1
    assert results["urls"][0] == "https://americanbazaaronline.com/2024/05/23/indian-american-led-ai-startup-secures-funding/"
    assert "https://americanbazaaronline.com/2024/05/22/new-ai-technology-unveiled/" not in results["urls"]
    assert "Paragraph from https://americanbazaaronline.com/2024/05/23/indian-american-led-ai-startup-secures-funding/" in results["paragraphs"]

@pytest.mark.asyncio
async def test_extract_paragraphs_from_american_bazaar_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from americanbazaaronline.com's specific HTML structure.
    """
    html_content = """
    <html><body>
        <div class="entry-content">
            <p>This is the first paragraph.</p>
            <p>This is the second, with <strong>bold text</strong>.</p>
            <p>  </p> <!-- This empty one should be ignored -->
        </div>
        <div class="another-div"><p>This paragraph should NOT be extracted.</p></div>
    </body></html>
    """
    test_url = "https://americanbazaaronline.com/fake-article"
    
    mock_html_response = MockResponse(html_content)
    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", AsyncMock(return_value=mock_html_response))

    url, paragraphs = await fetch.extract_paragraphs(None, test_url)

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
        "urls": ["https://americanbazaaronline.com/some-ai-funding-story/"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_american_bazaar_data", AsyncMock(return_value=fake_fetched_data))

    mock_ai_func = AsyncMock(return_value={"company_name": ["Test AI Co"]})
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    assert result is not None
    assert result["source"] == ["americanbazaaronline"]
    assert result["company_name"] == ["Test AI Co"]
    assert result["link"] == ["https://americanbazaaronline.com/some-ai-funding-story/"]
