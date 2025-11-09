import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

# Mock cloudscraper before importing fetch
sys.modules['cloudscraper'] = MagicMock()

from ingestion_module.funding.ventureburn import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Test that is_within_last_two_months correctly filters dates
@pytest.mark.asyncio
async def test_is_within_last_two_months_filters_recent_dates():
    recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert fetch_mod.is_within_last_two_months(recent_date) == True
    
    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert fetch_mod.is_within_last_two_months(old_date) == False
    
    assert fetch_mod.is_within_last_two_months(None) == False

# Test that parse_sitemap extracts URLs
@pytest.mark.asyncio
async def test_parse_sitemap_extracts_urls():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://ventureburn.com/article1</loc>
            <news:news>
                <news:publication_date>2025-11-05T12:00:00Z</news:publication_date>
            </news:news>
        </url>
    </urlset>
    """
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    articles = await fetch_mod.parse_sitemap(mock_client, "dummy_url")
    
    assert len(articles) > 0

# Test that is_ai_funding_related_content filters correctly
def test_is_ai_funding_related_content_filters_ai_and_funding():
    assert fetch_mod.is_ai_funding_related_content(
        "AI Startup Raises Funding",
        "The artificial intelligence company secured $10 million in Series A funding."
    ) == True
    
    assert fetch_mod.is_ai_funding_related_content(
        "AI Technology Advances",
        "Machine learning models are improving rapidly."
    ) == False

# Test that extract_and_filter_paragraphs extracts paragraphs
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_returns_paragraphs():
    html_content = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Test Article Title</h1>
            <div class="entry-content">
                <p>First paragraph with content about AI funding.</p>
                <p>Second paragraph with more details.</p>
            </div>
        </body>
    </html>
    """
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    
    mock_scraper = MagicMock()
    mock_scraper.get.return_value = mock_response
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = mock_response
        
        class MockAsyncClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
        
        mock_client = MockAsyncClient()
        semaphore = asyncio.Semaphore(1)
        
        url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
            mock_client, "http://test.com", semaphore
        )
        
        assert url == "http://test.com"
        assert len(paragraphs) >= 1  # Paragraphs may be combined or filtered

