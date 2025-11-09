import pytest
import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.venture_beat import fetch

########UPDATE THE COMMENTS ===================

# Helper class for mocking httpx responses
class MockResponse:
    def __init__(self, content, status_code=200, url="", headers=None):
        self.content = content.encode('utf-8')
        self.text = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {"Content-Type": "application/xml"}

    def raise_for_status(self):
        pass # In tests, we can just make this do nothing for successful responses. ***************explain*************

@pytest.mark.asyncio
async def test_fetch_venture_beat_data_happy_path(monkeypatch):
    """
    Tests that the main data fetching function correctly processes a sitemap,
    filters by both date and keywords, and returns the expected article link.
    """
    now = datetime.datetime.now(datetime.timezone.utc) # Make timezone-aware
    recent_date_str = now.isoformat()
    old_date_str = (now - datetime.timedelta(days=90)).isoformat()

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" 
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <!-- Case 1: Should be selected (recent date, has keywords) -->
        <url>
            <loc>https://venturebeat.com/ai/google-ai-secures-funding/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 2: Should be ignored (recent date, no keywords) -->
        <url>
            <loc>https://venturebeat.com/games/new-game-released/</loc>
            <n:publication_date>{recent_date_str}</n:publication_date>
        </url>
        <!-- Case 3: Should be ignored (has keywords, but old date) -->
        <url>
            <loc>https://venturebeat.com/ai/old-ai-funding-story/</loc>
            <n:publication_date>{old_date_str}</n:publication_date>
        </url>
        <!-- Case 4: Should be ignored (malformed date) -->
        <url>
            <loc>https://venturebeat.com/ai/another-funding-story/</loc>
            <n:publication_date>Not-A-Date</n:publication_date>
        </url>
    </urlset>
    """

    
    # Mock fetch_with_retries directly to return our mock response.
    mock_sitemap_response = MockResponse(sitemap_xml, 200, url="https://venturebeat.com/news-sitemap.xml")
    monkeypatch.setattr(fetch, "fetch_with_retries", AsyncMock(return_value=mock_sitemap_response))

    # Mock extract_paragraphs to avoid real network calls and return predictable data
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph from {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    # Run the function under test
    results = await fetch.fetch_venture_beat_data()

    # Assertions
    assert len(results["urls"]) == 1
    assert "https://venturebeat.com/ai/google-ai-secures-funding/" in results["urls"]
    assert "https://venturebeat.com/games/new-game-released/" not in results["urls"]
    assert "https://venturebeat.com/ai/old-ai-funding-story/" not in results["urls"]
    assert "Paragraph from https://venturebeat.com/ai/google-ai-secures-funding/" in results["paragraphs"][0]


@pytest.mark.asyncio
async def test_extract_paragraphs_from_venturebeat_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from VentureBeat's specific HTML structure.
    """
    html_content = """
    <html><body>
        <div class="article-body">
            <p>This is the first paragraph.</p>
            <p>This is the second, with <strong>bold text</strong>.</p>
            <p>  </p> <!-- This empty one should be ignored -->
            <div><p>This is a nested paragraph.</p></div>
        </div>
        <div class="another-div">
            <p>This paragraph should NOT be extracted.</p>
        </div>
    </body></html>
    """
    
    test_url = "https://venturebeat.com/fake-article"
    
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
        "urls": ["https://venturebeat.com/ai/google-ai-secures-funding/"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_venture_beat_data", AsyncMock(return_value=fake_fetched_data))

    # 2. Mock the AI extraction part to return a predictable result
    fake_ai_result = {"company_name": ["VentureAI"], "amount_raised": ["$50M"]}
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    # Run the main function
    result = await fetch.main()

    # Assert that the AI function was called with the correct data
    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    # Assert that the final output is correctly constructed
    assert result is not None
    assert result["source"] == ["venturebeat.com"]
    assert result["company_name"] == ["VentureAI"]
    assert result["amount_raised"] == ["$50M"]
    assert result["link"] == ["https://venturebeat.com/ai/google-ai-secures-funding/"]