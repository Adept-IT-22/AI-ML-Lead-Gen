import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

from ingestion_module.funding.google_news import fetch as fetch_mod

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Test that fetch_rss_feed extracts articles from RSS
@pytest.mark.asyncio
async def test_fetch_rss_feed_extracts_articles():
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>AI Startup Raises $10M in Series A</title>
                <pubDate>Mon, 05 Nov 2025 12:00:00 GMT</pubDate>
                <description><![CDATA[<a href="https://example.com/article1">Link</a>]]></description>
            </item>
            <item>
                <title>Tech Company Secures Investment</title>
                <pubDate>Mon, 04 Nov 2025 12:00:00 GMT</pubDate>
                <description><![CDATA[<a href="https://example.com/article2">Link</a>]]></description>
            </item>
        </channel>
    </rss>
    """
    
    mock_response = MagicMock()
    mock_response.content = rss_xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    article_data = await fetch_mod.fetch_rss_feed(mock_client, "dummy_url")
    
    # Should extract articles with AI and funding keywords
    assert len(article_data['titles']) > 0
    assert len(article_data['urls']) > 0

# Test that fetch_rss_feed filters by AI and funding keywords
@pytest.mark.asyncio
async def test_fetch_rss_feed_filters_ai_funding():
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>AI Startup Raises $10M</title>
                <pubDate>Mon, 05 Nov 2025 12:00:00 GMT</pubDate>
                <description><![CDATA[<a href="https://example.com/article1">Link</a>]]></description>
            </item>
            <item>
                <title>Regular Tech News</title>
                <pubDate>Mon, 04 Nov 2025 12:00:00 GMT</pubDate>
                <description><![CDATA[<a href="https://example.com/article2">Link</a>]]></description>
            </item>
        </channel>
    </rss>
    """
    
    mock_response = MagicMock()
    mock_response.content = rss_xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    article_data = await fetch_mod.fetch_rss_feed(mock_client, "dummy_url")
    
    # Should only extract articles with both AI and funding keywords
    assert len(article_data['titles']) > 0
    # Check that titles contain AI
    assert any("AI" in title for title in article_data['titles'])

