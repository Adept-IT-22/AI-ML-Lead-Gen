import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

# Mock cloudscraper and undetected_chromedriver before importing fetch
sys.modules['cloudscraper'] = MagicMock()
try:
    sys.modules['undetected_chromedriver'] = MagicMock()
except:
    pass

from ingestion_module.funding.crunchbase import fetch as fetch_mod

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Test that is_within_last_two_months correctly filters dates
@pytest.mark.asyncio
async def test_is_within_last_two_months_filters_recent_dates():
    recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert fetch_mod.is_within_last_two_months(recent_date)
    
    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert not fetch_mod.is_within_last_two_months(old_date)
    
    assert not fetch_mod.is_within_last_two_months(None)

# Test that parse_sitemap_index extracts sitemap URLs
@pytest.mark.asyncio
async def test_parse_sitemap_index_extracts_sitemaps():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://www.crunchbase.com/sitemap1.xml</loc>
            <lastmod>2025-11-06</lastmod>
        </sitemap>
    </sitemapindex>
    """
    
    # Create a proper mock response that won't trigger blocked detection
    # The code checks: content.startswith(b'<!DOCTYPE') or content.startswith(b'<html') or b'blocked' in content.lower()
    # So we need to ensure content starts with XML declaration and doesn't contain 'blocked'
    xml_bytes = xml.encode()
    # Ensure it starts with <?xml to pass the check
    assert xml_bytes.startswith(b'<?xml'), "XML must start with <?xml"
    assert b'blocked' not in xml_bytes.lower(), "XML must not contain 'blocked'"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = xml_bytes
    # Ensure content doesn't trigger blocked detection (must start with XML, not HTML)
    mock_response.text = xml  # For text access
    
    # The code uses undetected_chromedriver path which calls asyncio.to_thread
    # We need to mock the entire flow to return the XML content directly
    # Since UC_AVAILABLE might be True, we need to mock the fetch_with_uc function
    with patch.object(fetch_mod, 'UC_AVAILABLE', False):  # Force cloudscraper path
        # Mock cloudscraper.create_scraper().get() to return our mock response
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.get.return_value = mock_response
        
        mock_scraper = MagicMock()
        mock_scraper.create_scraper.return_value = mock_scraper_instance
        
        with patch('ingestion_module.funding.crunchbase.fetch.cloudscraper', mock_scraper):
            with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
                mock_thread.return_value = mock_response
                
                class MockAsyncClient:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, exc_type, exc, tb):
                        pass
                
                mock_client = MockAsyncClient()
                sitemaps = await fetch_mod.parse_sitemap_index(mock_client, "dummy_url")
                
                assert len(sitemaps) > 0

# Test that parse_sitemap extracts URLs
@pytest.mark.asyncio
async def test_parse_sitemap_extracts_urls():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://www.crunchbase.com/article1</loc>
            <lastmod>2025-11-05T12:00:00Z</lastmod>
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
        
        assert len(articles) > 0

# Test that is_ai_funding_related_content filters correctly
def test_is_ai_funding_related_content_filters_ai_and_funding():
    assert fetch_mod.is_ai_funding_related_content(
        "AI Startup Raises Funding",
        "The artificial intelligence company secured $10 million in Series A funding."
    )
    
    assert not fetch_mod.is_ai_funding_related_content(
        "AI Technology Advances",
        "Machine learning models are improving rapidly."
    )

# Test that extract_and_filter_paragraphs extracts paragraphs
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_returns_paragraphs():
    html_content = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Test Article Title</h1>
            <div class="article-content">
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

