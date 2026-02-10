import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.pr_news_wire import fetch

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
async def test_fetch_prnewswire_data_happy_path(monkeypatch):
    """
    Tests the two-level sitemap fetching for PR Newswire.
    Ensures it fetches the index, then the sub-sitemap, and correctly filters articles.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_date_str = now.isoformat()
    old_date_str = (now - datetime.timedelta(days=90)).isoformat()

    # Mock sitemap index file (level 1)
    sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://www.prnewswire.com/sitemap-news.xml?page=1</loc>
            <lastmod>2024-01-01T00:00:00-05:00</lastmod>
        </sitemap>
        <sitemap>
            <loc>https://www.prnewswire.com/sitemap-news.xml?page=2</loc>
            <lastmod>2024-01-01T00:00:00-05:00</lastmod>
        </sitemap>
    </sitemapindex>
    """

    # Mock sub-sitemap file with article links (level 2)
    sub_sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" 
            xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <!-- Case 1: Should be selected (recent date, has keywords) -->
        <url>
            <loc>https://www.prnewswire.com/news-releases/ai-startup-secures-funding-round-123.html</loc>
            <news:news><news:publication_date>{recent_date_str}</news:publication_date></news:news>
        </url>
        <!-- Case 2: Should be ignored (recent date, no AI keyword) -->
        <url>
            <loc>https://www.prnewswire.com/news-releases/company-raises-money-for-new-product-456.html</loc>
            <news:news><news:publication_date>{recent_date_str}</news:publication_date></news:news>
        </url>
        <!-- Case 3: Should be ignored (has keywords, but old date) -->
        <url>
            <loc>https://www.prnewswire.com/news-releases/old-ai-funding-story-789.html</loc>
            <news:news><news:publication_date>{old_date_str}</news:publication_date></news:news>
        </url>
    </urlset>
    """

    # Mock another sub-sitemap to ensure all are processed
    sub_sitemap_xml_page2 = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" 
            xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <!-- Case 4: Should be selected (recent date, has keywords) -->
        <url>
            <loc>https://www.prnewswire.com/news-releases/another-ai-company-lands-investment-abc.html</loc>
            <news:news><news:publication_date>{recent_date_str}</news:publication_date></news:news>
        </url>
    </urlset>
    """

    # Mock fetch_with_retries to handle the two-level fetch
    async def mock_fetch(client, url):
        if url == "https://www.prnewswire.com/sitemap-news.xml":
            return MockResponse(sitemap_index_xml)
        elif url == "https://www.prnewswire.com/sitemap-news.xml?page=1":
            return MockResponse(sub_sitemap_xml)
        elif url == "https://www.prnewswire.com/sitemap-news.xml?page=2":
            return MockResponse(sub_sitemap_xml_page2)
        return MockResponse("", status_code=404)

    monkeypatch.setattr(fetch, "fetch_with_retries", mock_fetch)

    # Mock extract_paragraphs to avoid real network calls
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    # Run the function under test
    results = await fetch.fetch_prnewswire_data()

    # Assertions
    expected_urls = [
        "https://www.prnewswire.com/news-releases/ai-startup-secures-funding-round-123.html",
        "https://www.prnewswire.com/news-releases/another-ai-company-lands-investment-abc.html"
    ]
    assert len(results["urls"]) == 2
    assert all(url in results["urls"] for url in expected_urls)
    assert "https://www.prnewswire.com/news-releases/company-raises-money-for-new-product-456.html" not in results["urls"]
    assert "Paragraph from https://www.prnewswire.com/news-releases/ai-startup-secures-funding-round-123.html" in results["paragraphs"]

@pytest.mark.asyncio
async def test_extract_paragraphs_from_prnewswire_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from PR Newswire's specific HTML structure.
    NOTE: The current `extract_paragraphs` function is generic. This test uses that generic structure.
    """
    html_content = """
    <html><body>
        <article class="clearfix">
            <p>This is the first paragraph.</p>
            <p>This is the second, with <strong>bold text</strong>.</p>
        </article>
    </body></html>
    """
    test_url = "https://www.prnewswire.com/fake-article"
    
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
        "urls": ["https://www.prnewswire.com/news-releases/ai-startup-secures-funding-round-123.html"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_prnewswire_data", AsyncMock(return_value=fake_fetched_data))

    fake_ai_result = {
        "company_name": ["PRWireAI"],
        "amount_raised": ["$25M"],
        "investors": ["PR Ventures"],
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    assert result is not None
    assert result["source"] == ["prnewswire.com"]
    assert result["company_name"] == ["PRWireAI"]
    assert result["amount_raised"] == ["$25M"]
    assert result["link"] == ["https://www.prnewswire.com/news-releases/ai-startup-secures-funding-round-123.html"]