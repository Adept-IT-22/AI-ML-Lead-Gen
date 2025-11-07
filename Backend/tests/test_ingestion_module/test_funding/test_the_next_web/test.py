import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.thenextweb import fetch

# Helper class for mocking httpx responses
class MockResponse:
    def __init__(self, content, status_code=200, url="", headers=None):
        self.content = content.encode('utf-8')
        self.text = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {"Content-Type": "application/xml"}

    def raise_for_status(self):
        pass # In tests, we can just make this do nothing for successful responses.

@pytest.mark.asyncio
async def test_fetch_thenextweb_data_multi_level_sitemap(monkeypatch):
    """
    Tests that the function correctly handles a multi-level sitemap,
    filtering by date at both levels and by keywords at the article level.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_date_str = now.isoformat()
    old_date_str = (now - datetime.timedelta(days=90)).isoformat()

    # 1. Mock the PARENT sitemap index
    sitemap_index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- This child sitemap is recent and should be fetched -->
        <sitemap>
            <loc>https://thenextweb.com/sitemap-articles-recent.xml</loc>
            <lastmod>{recent_date_str}</lastmod>
        </sitemap>
        <!-- This child sitemap is old and should be ignored -->
        <sitemap>
            <loc>https://thenextweb.com/sitemap-articles-old.xml</loc>
            <lastmod>{old_date_str}</lastmod>
        </sitemap>
    </sitemapindex>
    """

    # 2. Mock the CHILD sitemap containing articles
    child_sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <!-- Provide only one valid article to simplify the test -->
        <url>
            <loc>https://thenextweb.com/news/belgian-ai-agent-startup-ravical-funding</loc>
            <lastmod>{recent_date_str}</lastmod>
        </url>
    </urlset>
    """

    # 3. Mock fetch_with_retries to return different responses based on URL
    # Use a dictionary for a more robust mock that maps exact URLs to responses.
    response_map = {
        "https://thenextweb.com/sitemap-articles-index.xml": MockResponse(sitemap_index_xml, url="https://thenextweb.com/sitemap-articles-index.xml"),
        "https://thenextweb.com/sitemap-articles-recent.xml": MockResponse(child_sitemap_xml, url="https://thenextweb.com/sitemap-articles-recent.xml"),
    }

    async def fake_fetch(client, url, **kwargs):
        # Return the correct response from the map, or a 404 if the URL is not expected.
        # The call for "sitemap-articles-old.xml" will correctly fail here.
        return response_map.get(url, MockResponse("<xml/>", 404, url=url))
    monkeypatch.setattr(fetch, "fetch_with_retries", fake_fetch)

    
    # This mock must return the URL it was called with.
    async def fake_extract(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract)

    # Run the function under test
    results = await fetch.fetch_thenextweb_data()

    # Assertions
    assert len(results["urls"]) == 1
    assert "https://thenextweb.com/news/belgian-ai-agent-startup-ravical-funding" in results["urls"]

@pytest.mark.asyncio
async def test_extract_paragraphs_from_thenextweb_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from TheNextWeb's HTML structure.
    """
    html_content = """
    <html><body>
        <div class="c-article__main">
            <p>This is the first paragraph.</p>
            <p>This is the second.</p>
        </div>
        <div class="another-div">
            <p>This paragraph should NOT be extracted.</p>
        </div>
    </body></html>
    """
    
    test_url = "https://thenextweb.com/fake-article"
    mock_html_response = MockResponse(html_content, 200, url=test_url, headers={"Content-Type": "text/html"})
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_html_response

    # Run the function under test
    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    # Assertions
    assert url == test_url
    assert len(paragraphs) == 2
    assert paragraphs[0] == "This is the first paragraph."

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    fake_fetched_data = {
        "urls": ["https://thenextweb.com/news/belgian-ai-agent-startup-ravical-funding"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_thenextweb_data", AsyncMock(return_value=fake_fetched_data))

    fake_ai_result = {"company_name": ["Ravioli AI"], "amount_raised": ["€10M"]}
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    # Run the main function
    result = await fetch.main()

    # Assertions
    assert result is not None
    assert result["source"] == ["thenextweb.com"]
    assert result["company_name"] == ["Ravioli AI"]
    assert result["link"] == fake_fetched_data["urls"]