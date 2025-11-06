import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

# Mock cloudscraper before importing fetch
sys.modules['cloudscraper'] = MagicMock()

from ingestion_module.funding.businessinsider_africa import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import gzip

# Test that is_within_last_two_months correctly filters dates
@pytest.mark.asyncio
async def test_is_within_last_two_months_filters_recent_dates():
    recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert fetch_mod.is_within_last_two_months(recent_date) == True
    
    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert fetch_mod.is_within_last_two_months(old_date) == False
    
    assert fetch_mod.is_within_last_two_months(None) == False

# Test that fetch_and_decompress_gz decompresses gzip content
@pytest.mark.asyncio
async def test_fetch_and_decompress_gz_decompresses_content():
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://africa.businessinsider.com/article1</loc></url>
    </urlset>
    """
    compressed = gzip.compress(xml_content)
    
    mock_response = MagicMock()
    mock_response.content = compressed
    
    mock_scraper = MagicMock()
    mock_scraper.get.return_value = mock_response
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = mock_response
        
        result = await fetch_mod.fetch_and_decompress_gz(mock_scraper, "dummy_url")
        
        assert result is not None
        assert b"<?xml" in result

# Test that parse_sitemap extracts URLs
@pytest.mark.asyncio
async def test_parse_sitemap_extracts_urls():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://africa.businessinsider.com/article1</loc>
            <news:news>
                <news:publication_date>2025-11-05T12:00:00Z</news:publication_date>
            </news:news>
        </url>
    </urlset>
    """
    
    # Mock the decompressed content (after gzip decompression)
    decompressed_content = xml.encode()
    
    # Mock fetch_and_decompress_gz to return decompressed content
    with patch.object(fetch_mod, 'fetch_and_decompress_gz', new_callable=AsyncMock) as mock_decompress:
        mock_decompress.return_value = decompressed_content
        
        mock_scraper = MagicMock()
        articles = await fetch_mod.parse_sitemap(mock_scraper, "dummy_url")
        
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

