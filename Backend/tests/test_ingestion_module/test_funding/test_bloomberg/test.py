import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

# Mock cloudscraper before importing fetch
sys.modules['cloudscraper'] = MagicMock()

from ingestion_module.funding.bloomberg import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Test that is_within_last_two_months correctly filters dates
@pytest.mark.asyncio
async def test_is_within_last_two_months_filters_recent_dates():
    # Test with a recent date (within last 2 months)
    recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert fetch_mod.is_within_last_two_months(recent_date)
    
    # Test with an old date (more than 2 months ago)
    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert not fetch_mod.is_within_last_two_months(old_date)
    
    # Test with None (should exclude - fail closed)
    assert not fetch_mod.is_within_last_two_months(None)
    
    # Test with invalid date (should exclude - fail closed)
    assert not fetch_mod.is_within_last_two_months("invalid-date")

# Test that parse_sitemap_index extracts sitemap URLs
@pytest.mark.asyncio
async def test_parse_sitemap_index_extracts_sitemaps():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://www.bloomberg.com/sitemaps/news/2025-11.xml</loc>
            <lastmod>2025-11-06</lastmod>
        </sitemap>
        <sitemap>
            <loc>https://www.bloomberg.com/sitemaps/news/2025-10.xml</loc>
            <lastmod>2025-10-31</lastmod>
        </sitemap>
    </sitemapindex>
    """
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = xml.encode()
    mock_response.headers = {'Content-Encoding': ''}
    
    # Mock cloudscraper
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
        sitemaps = await fetch_mod.parse_sitemap_index(mock_client, "dummy_url")
        
        # Should extract sitemap URLs
        assert len(sitemaps) > 0

# Test that parse_sitemap extracts URLs with dates
@pytest.mark.asyncio
async def test_parse_sitemap_extracts_urls():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://www.bloomberg.com/news/articles/2025-11-05/article1</loc>
            <lastmod>2025-11-05T12:00:00Z</lastmod>
            <news:news>
                <news:publication_date>2025-11-05T12:00:00Z</news:publication_date>
            </news:news>
        </url>
        <url>
            <loc>https://www.bloomberg.com/news/articles/2025-10-09/article2</loc>
            <lastmod>2025-10-09T22:09:00Z</lastmod>
            <news:news>
                <news:publication_date>2025-10-09T22:09:00Z</news:publication_date>
            </news:news>
        </url>
    </urlset>
    """
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = xml.encode()
    
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
        articles = await fetch_mod.parse_sitemap(mock_client, "dummy_url")
        
        # Should extract URLs
        assert len(articles) > 0
        urls = [article['url'] for article in articles]
        assert any("article1" in url for url in urls) or any("article2" in url for url in urls)

# Test that is_ai_funding_related_content filters correctly
def test_is_ai_funding_related_content_filters_ai_and_funding():
    # Test with AI and funding keywords
    assert fetch_mod.is_ai_funding_related_content(
        "AI Startup Raises Funding",
        "The artificial intelligence company secured $10 million in Series A funding."
    ) == True
    
    # Test with only AI keywords (no funding)
    assert fetch_mod.is_ai_funding_related_content(
        "AI Technology Advances",
        "Machine learning models are improving rapidly."
    ) == False
    
    # Test with only funding keywords (no AI)
    assert fetch_mod.is_ai_funding_related_content(
        "Tech Startup Secures Investment",
        "The company secured $10 million in Series B funding from venture capital investors."
    ) == False
    
    # Test with neither AI nor funding
    assert fetch_mod.is_ai_funding_related_content(
        "Regular News Article",
        "This is just a regular news article about technology."
    ) == False

# Test that extract_and_filter_paragraphs extracts paragraphs
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_returns_paragraphs():
    html_content = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Test Article Title</h1>
            <div class="body-content">
                <p class="ArticleBodyText_articleBodyContent__17wqE typography_articleBody__3UcBa" data-component="paragraph">
                    The National Highway Traffic Safety Administration said today that it has opened a probe.
                </p>
                <p class="ArticleBodyText_articleBodyContent__17wqE typography_articleBody__3UcBa" data-component="paragraph">
                    About 2.8 million Tesla vehicles with the company's Full Self-Driving system will be scrutinized.
                </p>
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
        assert title == "Test Article Title"
        assert len(paragraphs) >= 2

# Test that extract_and_filter_paragraphs handles errors gracefully
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_handles_errors():
    mock_scraper = MagicMock()
    mock_scraper.get.side_effect = Exception("Network error")
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("Network error")
        
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
        assert paragraphs == []
        assert title == ""

