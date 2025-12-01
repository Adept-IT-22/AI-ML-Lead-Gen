import pytest
from unittest.mock import patch, AsyncMock
import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.geekwire import fetch

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

MOCK_SITEMAP_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <sitemap>
      <loc>https://www.geekwire.com/sitemap-misc.xml</loc>
      <lastmod>2025-11-10T19:03:41Z</lastmod>
   </sitemap>
   <sitemap>
      <loc>https://www.geekwire.com/sitemap-54.xml</loc>
      <lastmod>2025-11-10T19:03:41Z</lastmod> <!-- Tie: Should be picked due to higher number -->
   </sitemap>
   <sitemap>
      <loc>https://www.geekwire.com/sitemap-53.xml</loc>
      <lastmod>2025-11-10T19:03:41Z</lastmod> <!-- Tie: Should be ignored -->
   </sitemap>
   <sitemap>
      <loc>https://www.geekwire.com/sitemap-52.xml</loc>
      <lastmod>2025-10-01T12:00:00Z</lastmod>
   </sitemap>
</sitemapindex>
"""

MOCK_POST_SITEMAP_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://www.geekwire.com/2025/valid-article-ai-funding/</loc>
      <lastmod>{(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)).isoformat().replace('+00:00', 'Z')}</lastmod>
   </url>
   <url>
      <loc>https://www.geekwire.com/2025/old-article-ai-funding/</loc>
      <lastmod>{(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat().replace('+00:00', 'Z')}</lastmod>
   </url>
   <url>
      <loc>https://www.geekwire.com/2025/no-keyword-article/</loc>
      <lastmod>{(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)).isoformat().replace('+00:00', 'Z')}</lastmod>
   </url>
</urlset>
"""

MOCK_ARTICLE_HTML = """
<html>
<body>
  <article class="clearfix">
    <h1>Title</h1>
    <p>This is the first paragraph about AI and funding.</p>
    <p>This is the second paragraph.</p>
    <div><p>This paragraph is nested and should be found.</p></div>
    <p></p> <!-- Empty paragraph -->
  </article>
  <div class="another-section">
    <p>This paragraph should NOT be extracted.</p>
  </div>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_fetch_geekwire_data_happy_path(monkeypatch, caplog):
    """
    Tests the successful path of fetch_geekwire_data:
    - Selects the correct sitemap using date and number tie-breaker.
    - Filters articles by date and keywords.
    - Extracts paragraphs from the valid article.
    """
    # Mock the cloudscraper responses
    async def mock_fetch(client, url):
        if url == "https://www.geekwire.com/sitemap-index-1.xml":
            return MockResponse(MOCK_SITEMAP_INDEX_XML)
        elif url == "https://www.geekwire.com/sitemap-54.xml": # This is the one that should be fetched
            return MockResponse(MOCK_POST_SITEMAP_XML)
        elif url == "https://www.geekwire.com/2025/valid-article-ai-funding/":
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        else:
            # Any other URL call is unexpected
            return MockResponse("", status_code=404)

    # Patch the function that makes the actual network calls
    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)

    caplog.set_level("INFO")

    # Run the function to be tested
    results = await fetch.fetch_geekwire_data()

    # --- Assertions ---

    # Check if the correct sitemap was processed
    found_log = "Processing latest sitemap: https://www.geekwire.com/sitemap-54.xml" in caplog.text
    assert found_log, "Log message for processing the correct sitemap not found."

    # Check if the final results contain the correct URL and paragraphs
    assert len(results['urls']) == 1
    assert results['urls'][0] == "https://www.geekwire.com/2025/valid-article-ai-funding/"
    assert len(results['paragraphs']) == 1
    expected_paragraphs = "This is the first paragraph about AI and funding.\nThis is the second paragraph.\nThis paragraph is nested and should be found."
    assert results['paragraphs'][0] == expected_paragraphs

@pytest.mark.asyncio
async def test_extract_paragraphs_from_geekwire_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from GeekWire's specific HTML structure.
    """
    test_url = "https://www.geekwire.com/fake-article"
    
    # Mock the network call within extract_paragraphs
    async def mock_fetch(client, url):
        if url == test_url:
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        return MockResponse("", status_code=404)
    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)

    # Call the function directly to test it in isolation
    mock_client = AsyncMock() # A dummy client object
    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    assert url == test_url
    assert len(paragraphs) == 3 # Checks that all 3 paragraphs are found
    assert paragraphs[0] == "This is the first paragraph about AI and funding."
    assert paragraphs[1] == "This is the second paragraph."
    assert paragraphs[2] == "This paragraph is nested and should be found."

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    # Mock the data fetching part to return predictable data
    fake_fetched_data = {
        "urls": ["https://www.geekwire.com/2025/valid-article-ai-funding/"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_geekwire_data", AsyncMock(return_value=fake_fetched_data))

    # Mock AI extraction part to return a predictable result
    fake_ai_result = { 
        "company_name": ["GeekAI Inc."],
        "amount_raised": ["$10M"],
        "investors": ["Geek Ventures"],
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    # Run the main function
    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    # Assert the final output is constructed as expected
    assert result is not None
    assert "geekwire" in result["source"]
    assert "GeekAI Inc." in result["company_name"]
    assert "$10M" in result["amount_raised"]
    assert "https://www.geekwire.com/2025/valid-article-ai-funding/" in result["link"]