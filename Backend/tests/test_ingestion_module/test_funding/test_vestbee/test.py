import pytest
from unittest.mock import patch, AsyncMock
import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.vestbee import fetch

# Helper class for mocking responses
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

# --- Mock Data ---

NOW = datetime.datetime.now(datetime.timezone.utc)
RECENT_DATE_ISO = (NOW - datetime.timedelta(days=5)).isoformat().replace('+00:00', 'Z')
OLD_DATE_ISO = (NOW - datetime.timedelta(days=90)).isoformat().replace('+00:00', 'Z')

MOCK_SITEMAP_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://www.vestbee.com/blog/ai-startup-secures-funding</loc>
      <lastmod>{RECENT_DATE_ISO}</lastmod>
   </url>
   <url>
      <loc>https://www.vestbee.com/blog/old-article-about-ai-funding</loc>
      <lastmod>{OLD_DATE_ISO}</lastmod>
   </url>
   <url>
      <loc>https://www.vestbee.com/blog/article-about-ai-innovations</loc>
      <lastmod>{RECENT_DATE_ISO}</lastmod>
   </url>
   <url>
      <loc>https://www.vestbee.com/blog/company-raises-money-for-hardware</loc>
      <lastmod>{RECENT_DATE_ISO}</lastmod>
   </url>
</urlset>
"""

MOCK_ARTICLE_HTML = """
<html>
<body>
  <div class="article-content">
    <p>This is the first paragraph of the Vestbee article.</p>
    <p>It contains details about the AI funding round.</p>
    <p></p> <!-- Empty paragraph -->
  </div>
  <div class="some-other-div">
    <p>This paragraph should NOT be extracted.</p>
  </div>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_fetch_vestbee_data_happy_path(monkeypatch, caplog):
    """
    Tests the successful path of fetch_vestbee_data:
    - Fetches the sitemap.
    - Filters articles by date and keywords in the URL.
    - Extracts paragraphs from the valid article.
    """
    async def mock_fetch(client, url):
        if url == fetch.URL[0]:
            return MockResponse(MOCK_SITEMAP_XML)
        elif url == "https://www.vestbee.com/blog/ai-startup-secures-funding":
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        else:
            return MockResponse("", status_code=404)

    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)
    caplog.set_level("INFO")

    results = await fetch.fetch_vestbee_data()

    # Assertions
    assert len(results['urls']) == 1
    assert results['urls'][0] == "https://www.vestbee.com/blog/ai-startup-secures-funding"

    assert len(results['paragraphs']) == 1
    expected_paragraphs = "This is the first paragraph of the Vestbee article.\nIt contains details about the AI funding round."
    assert results['paragraphs'][0] == expected_paragraphs

    assert "Found 1 articles matching all filters." in caplog.text

@pytest.mark.asyncio
async def test_extract_paragraphs_from_vestbee_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from Vestbee's specific HTML structure.
    """
    test_url = "https://www.vestbee.com/test-article"
    
    async def mock_fetch(client, url):
        if url == test_url:
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        return MockResponse("", status_code=404)
    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)

    mock_client = AsyncMock() # A dummy client object
    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    assert url == test_url
    assert len(paragraphs) == 2
    assert paragraphs[0] == "This is the first paragraph of the Vestbee article."
    assert paragraphs[1] == "It contains details about the AI funding round."

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    fake_fetched_data = {
        "urls": ["https://www.vestbee.com/fake-article-1"],
        "paragraphs": ["A paragraph about AI and funding from Vestbee."]
    }
    monkeypatch.setattr(fetch, "fetch_vestbee_data", AsyncMock(return_value=fake_fetched_data))

    fake_ai_result = {
        "company_name": ["Vestbee AI Corp."],
        "amount_raised": ["€2M"],
        "investors": ["Vestbee Ventures"],
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    assert result is not None
    assert "vestbee.com" in result["source"]
    assert "Vestbee AI Corp." in result["company_name"]
    assert "€2M" in result["amount_raised"]
    assert "https://www.vestbee.com/fake-article-1" in result["link"]
