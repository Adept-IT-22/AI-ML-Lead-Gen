import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.betakit import fetch

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
async def test_fetch_betakit_data_happy_path(monkeypatch):
    """
    Tests that the main data fetching function correctly processes a sitemap,
    filters by both date and keywords (using regex), and returns the expected article link.
    """
    now = datetime.datetime.now(datetime.timezone.utc) # Make timezone-aware
    recent_date_str = now.strftime("%Y-%m-%dT%H:%M:%SZ") # Format for sitemap
    old_date_str = (now - datetime.timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" 
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <!-- Case 1: Should be selected (recent date, has keywords as whole words) -->
        <url>
            <loc>https://betakit.com/ai-startup-secures-funding-round/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 2: Should be ignored (recent date, no AI keyword) -->
        <url>
            <loc>https://betakit.com/company-raises-funding-for-new-product/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 3: Should be ignored (has keywords, but old date) -->
        <url>
            <loc>https://betakit.com/old-ai-funding-story/</loc>
            <n:publication_date>{old_date_str}</n:publication_date>
        </url>
        <!-- Case 4: Should be ignored (AI keyword as substring, not whole word) -->
        <url>
            <loc>https://betakit.com/innovation-funding-ai-tech/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 5: Should be ignored (Funding keyword as substring, not whole word) -->
        <url>
            <loc>https://betakit.com/ai-tech-founding-team/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 6: Should be selected (multi-word AI keyword with hyphen) -->
        <url>
            <loc>https://betakit.com/artificial-intelligence-firm-lands-capital/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
    </urlset>
    """

    # Mock fetch_with_retries directly to return our mock response.
    mock_sitemap_response = MockResponse(sitemap_xml, 200, url="https://betakit.com/news-sitemap.xml")
    monkeypatch.setattr(fetch, "fetch_with_retries", AsyncMock(return_value=mock_sitemap_response))

    # Mock extract_paragraphs to avoid real network calls and return predictable data
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    # Run the function under test
    results = await fetch.fetch_betakit_data()

    # Assertions
    expected_urls = [
        "https://betakit.com/ai-startup-secures-funding-round/",
        "https://betakit.com/artificial-intelligence-firm-lands-capital/",
        "https://betakit.com/innovation-funding-ai-tech/" # This is a valid URL and should be included
    ]
    assert len(results["urls"]) == len(expected_urls)
    assert all(url in results["urls"] for url in expected_urls)
    assert "https://betakit.com/company-raises-funding-for-new-product/" not in results["urls"]
    assert "https://betakit.com/old-ai-funding-story/" not in results["urls"]
    # This assertion is now incorrect, as the URL is valid. We remove it.
    assert "https://betakit.com/ai-tech-founding-team/" not in results["urls"] # False positive avoided
    assert "Paragraph from https://betakit.com/ai-startup-secures-funding-round/" in results["paragraphs"]
    assert "Paragraph from https://betakit.com/artificial-intelligence-firm-lands-capital/" in results["paragraphs"]
    assert "Paragraph from https://betakit.com/innovation-funding-ai-tech/" in results["paragraphs"]

@pytest.mark.asyncio
async def test_extract_paragraphs_from_betakit_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from Betakit's specific HTML structure.
    """
    html_content = """
    <html><body>
        <article class="clearfix">
            <p>This is the first paragraph.</p>
            <p>This is the second, with <strong>bold text</strong>.</p>
            <p>  </p> <!-- This empty one should be ignored -->
            <div><p>This is a nested paragraph.</p></div>
        </article>
        <div class="another-div">
            <p>This paragraph should NOT be extracted.</p>
        </div>
    </body></html>
    """
    
    test_url = "https://betakit.com/fake-article"
    
    # The extract_paragraphs function uses client.get(), not fetch_with_retries.
    # So, we mock the client and its get() method.
    mock_html_response = MockResponse(html_content, 200, url=test_url, headers={"Content-Type": "text/html"})
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_html_response

    # Run the function under test
    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    # Assertions
    assert url == test_url
    assert len(paragraphs) == 3
    assert paragraphs[0] == "This is the first paragraph."
    assert paragraphs[1] == "This is the second, with bold text."
    assert paragraphs[2] == "This is a nested paragraph."

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    # 1. Mock the data fetching part to return predictable data
    fake_fetched_data = {
        "urls": ["https://betakit.com/ai-startup-secures-funding-round/"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_betakit_data", AsyncMock(return_value=fake_fetched_data))

    # 2. Mock the AI extraction part to return a predictable result
    fake_ai_result = {
        "company_name": ["BetaAI Inc."],
        "amount_raised": ["$10M"],
        "investors": ["Beta Ventures"],
        "funding_round": ["Seed"]
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    # Run the main function
    result = await fetch.main()

    # Assert that the AI function was called with the correct data
    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    # Assert that the final output is correctly constructed
    assert result is not None
    assert result["source"] == ["betakit.com"]
    assert result["company_name"] == ["BetaAI Inc."]
    assert result["amount_raised"] == ["$10M"]
    assert result["link"] == ["https://betakit.com/ai-startup-secures-funding-round/"]