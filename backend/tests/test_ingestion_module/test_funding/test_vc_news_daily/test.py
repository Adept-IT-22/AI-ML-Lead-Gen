import pytest
from unittest.mock import patch, AsyncMock
import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ingestion_module.funding.vc_news_daily import fetch

# Helper class for mocking responses
class MockResponse:
    def __init__(self, content, status_code=200, url="", headers=None):
        self.content = content.encode('utf-8')
        self.text = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {"Content-Type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")

# --- Mock Data ---

# Dynamic dates for testing date filtering
NOW = datetime.datetime.now(datetime.timezone.utc)
RECENT_DATE_STR = (NOW - datetime.timedelta(days=5)).strftime("%d %B %Y") # e.g., "10 November 2025"
OLD_DATE_STR = (NOW - datetime.timedelta(days=90)).strftime("%d %B %Y") # e.g., "10 August 2025

MOCK_MAIN_PAGE_HTML = f"""
<html>
<body>
    <div class="col-md-6 mb-4">
        <div class="col-md-8">
            <a href="https://vcnewsdaily.com/valid-ai-funding-article">Valid AI Funding Article Title</a>
            <small class="posted-date">{RECENT_DATE_STR}</small>
            <p class="article-paragraph mb-0">This startup secured funding for its AI platform.</p>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="col-md-8">
            <a href="https://vcnewsdaily.com/old-article">Old Article Title</a>
            <small class="posted-date">{OLD_DATE_STR}</small>
            <p class="article-paragraph mb-0">This is an old article about a company.</p>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="col-md-8">
            <a href="https://vcnewsdaily.com/no-ai-article">No AI Keyword Article Title</a>
            <small class="posted-date">{RECENT_DATE_STR}</small>
            <p class="article-paragraph mb-0">This company raises capital for its new project.</p>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="col-md-8">
            <a href="https://vcnewsdaily.com/no-funding-article">No Funding Keyword Article Title</a>
            <small class="posted-date">{RECENT_DATE_STR}</small>
            <p class="article-paragraph mb-0">This is about a new AI development.</p>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="col-md-8">
            <a href="https://vcnewsdaily.com/another-valid-article">Another Valid Article Title</a>
            <small class="posted-date">{RECENT_DATE_STR}</small>
            <p class="article-paragraph mb-0">A machine learning firm lands significant investment.</p>
        </div>
    </div>
</body>
</html>
"""

MOCK_ARTICLE_HTML = """
<html>
<body>
  <div id="fullArticle" class="fullArticle">
    This is the first paragraph of the article.
    <br/><br/>
    It contains details about the AI funding round.
    Another nested paragraph.
  </div>
  <div class="some-other-div">
    <p>This paragraph should NOT be extracted.</p>
  </div>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_fetch_vc_news_daily_data_happy_path(monkeypatch, caplog):
    """
    Tests the successful path of fetch_vc_news_daily_data:
    - Fetches the main page.
    - Filters articles by date and keywords in description.
    - Extracts paragraphs from the valid articles.
    """
    async def mock_fetch(client, url):
        if url == fetch.URL:
            return MockResponse(MOCK_MAIN_PAGE_HTML)
        elif url == "https://vcnewsdaily.com/valid-ai-funding-article":
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        elif url == "https://vcnewsdaily.com/another-valid-article":
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        else:
            return MockResponse("", status_code=404)

    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)
    caplog.set_level("INFO")

    results = await fetch.fetch_vc_news_daily_data()

    # Assertions
    assert len(results['urls']) == 2
    assert "https://vcnewsdaily.com/valid-ai-funding-article" in results['urls']
    assert "https://vcnewsdaily.com/another-valid-article" in results['urls']

    assert len(results['paragraphs']) == 2
    expected_paragraphs = "This is the first paragraph of the article.\n    \n    It contains details about the AI funding round.\n    Another nested paragraph."
    assert results['paragraphs'][0] == expected_paragraphs

    assert "Found 2 articles matching all filters." in caplog.text

@pytest.mark.asyncio
async def test_extract_paragraphs_from_vc_news_daily_html(monkeypatch):
    """
    Tests that paragraphs are correctly extracted from VC News Daily's specific HTML structure.
    """
    test_url = "https://vcnewsdaily.com/test-article"
    
    async def mock_fetch(client, url):
        if url == test_url:
            return MockResponse(MOCK_ARTICLE_HTML, headers={"Content-Type": "text/html"})
        return MockResponse("", status_code=404)
    monkeypatch.setattr(fetch, "fetch_with_cloudscraper", mock_fetch)

    mock_client = AsyncMock() # A dummy client object
    url, paragraphs = await fetch.extract_paragraphs(mock_client, test_url)

    assert url == test_url
    # Assert that we get ONE block of text, as per the HTML structure
    assert len(paragraphs) == 1
    assert "This is the first paragraph of the article." in paragraphs[0]
    assert "Another nested paragraph." in paragraphs[0]

@pytest.mark.asyncio
async def test_main_integration_with_ai_extraction(monkeypatch):
    """
    Tests the main function's integration, ensuring it calls the AI module correctly.
    """
    fake_fetched_data = {
        "urls": ["https://vcnewsdaily.com/fake-article-1"],
        "paragraphs": ["A paragraph about AI and funding."]
    }
    monkeypatch.setattr(fetch, "fetch_vc_news_daily_data", AsyncMock(return_value=fake_fetched_data))

    fake_ai_result = {
        "company_name": ["VC AI Corp."],
        "amount_raised": ["$20M"],
        "investors": ["Daily Ventures"],
    }
    mock_ai_func = AsyncMock(return_value=fake_ai_result)
    monkeypatch.setattr(fetch, "finalize_ai_extraction", mock_ai_func)

    result = await fetch.main()

    mock_ai_func.assert_called_once_with(links_and_paragraphs=fake_fetched_data)

    assert result is not None
    assert "vcnewsdaily.com" in result["source"]
    assert "VC AI Corp." in result["company_name"]
    assert "$20M" in result["amount_raised"]
    assert "https://vcnewsdaily.com/fake-article-1" in result["link"]