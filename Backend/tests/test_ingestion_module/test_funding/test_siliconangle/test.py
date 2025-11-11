import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()

from ingestion_module.funding.siliconangle import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Test that is_within_last_two_months correctly filters dates
@pytest.mark.asyncio
async def test_is_within_last_two_months_filters_recent_dates():
    # Test with a recent date (within last 2 months)
    recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S%z")
    assert fetch_mod.is_within_last_two_months(recent_date)
    
    # Test with an old date (more than 2 months ago)
    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert not fetch_mod.is_within_last_two_months(old_date)
    
    # Test with None (should include)
    assert fetch_mod.is_within_last_two_months(None)
    
    # Test with invalid date (should include)
    assert fetch_mod.is_within_last_two_months("invalid-date")

# Test that parse_sitemap_index returns relevant sitemap URLs with lastmod
@pytest.mark.asyncio
async def test_parse_sitemap_index_returns_relevant_urls():
    # Simulate XML with sitemaps, some matching relevant patterns
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://siliconangle.com/post-sitemap75.xml</loc>
            <lastmod>2025-11-05T03:14:04-05:00</lastmod>
        </sitemap>
        <sitemap>
            <loc>https://siliconangle.com/page-sitemap.xml</loc>
            <lastmod>2025-11-03T15:10:00-05:00</lastmod>
        </sitemap>
        <sitemap>
            <loc>https://siliconangle.com/post-sitemap74.xml</loc>
            <lastmod>2025-10-09T22:09:00-04:00</lastmod>
        </sitemap>
    </sitemapindex>
    """
    
    mock_response = MagicMock()
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    # Create a mock AsyncClient
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    
    # Test the function
    sitemap_entries = await fetch_mod.parse_sitemap_index(mock_client, "dummy_url")
    
    # Should only return post-sitemap URLs
    urls = [entry['url'] for entry in sitemap_entries]
    assert "https://siliconangle.com/post-sitemap75.xml" in urls
    assert "https://siliconangle.com/post-sitemap74.xml" in urls
    assert "https://siliconangle.com/page-sitemap.xml" not in urls
    
    # Check lastmod dates are included
    assert any(entry['lastmod'] == "2025-11-05T03:14:04-05:00" for entry in sitemap_entries)
    assert any(entry['lastmod'] == "2025-10-09T22:09:00-04:00" for entry in sitemap_entries)

# Test that parse_sitemap extracts URLs with lastmod dates
@pytest.mark.asyncio
async def test_parse_sitemap_extracts_urls():
    # Simulate sitemap XML with article URLs
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://siliconangle.com/2025/10/09/article1.html</loc>
            <lastmod>2025-10-09T22:09:00-04:00</lastmod>
        </url>
        <url>
            <loc>https://siliconangle.com/2025/11/05/article2.html</loc>
            <lastmod>2025-11-05T03:14:04-05:00</lastmod>
        </url>
    </urlset>
    """
    
    mock_response = MagicMock()
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    # Create a mock AsyncClient
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    
    # Test the function
    articles = await fetch_mod.parse_sitemap(mock_client, "dummy_url")
    
    # Should extract both URLs
    urls = [article['url'] for article in articles]
    assert "https://siliconangle.com/2025/10/09/article1.html" in urls
    assert "https://siliconangle.com/2025/11/05/article2.html" in urls
    
    # Check lastmod dates are included
    assert len(articles) == 2
    assert articles[0]['lastmod'] == "2025-10-09T22:09:00-04:00"
    assert articles[1]['lastmod'] == "2025-11-05T03:14:04-05:00"

# Test that is_ai_funding_related_content filters correctly
def test_is_ai_funding_related_content_filters_ai_and_funding():
    # Test with AI and funding keywords
    assert fetch_mod.is_ai_funding_related_content(
        "AI Startup Raises Funding",
        "The artificial intelligence company secured $10 million in Series A funding."
    )
    
    # Test with only AI keywords (no funding)
    assert not fetch_mod.is_ai_funding_related_content(
        "AI Technology Advances",
        "Machine learning models are improving rapidly."
    )
    
    # Test with only funding keywords (no AI)
    assert not fetch_mod.is_ai_funding_related_content(
        "Tech Startup Secures Investment",
        "The company secured $10 million in Series B funding from venture capital investors."
    )
    
    # Test with neither AI nor funding
    assert not fetch_mod.is_ai_funding_related_content(
        "Regular News Article",
        "This is just a regular news article about technology."
    )
    
    # Test with LLM (large language model) keyword
    assert fetch_mod.is_ai_funding_related_content(
        "LLM Startup Closes Round",
        "The large language model company closed a funding round."
    )

# Test that extract_and_filter_paragraphs extracts paragraphs from single-post-content
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_returns_paragraphs():
    html_content = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Test Article Title</h1>
            <div class="single-post-content">
                <p>The National Highway Traffic Safety Administration said today that it has opened a probe.</p>
                <p>About 2.8 million Tesla vehicles with the company's Full Self-Driving system will be scrutinized.</p>
                <div class="silic-after-content" id="silic-128311010">
                    <p>This is footer content that should be excluded.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    
    # Create a mock AsyncClient
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    semaphore = asyncio.Semaphore(1)
    
    # Test the function
    url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
        mock_client, "http://test.com", semaphore
    )
    
    assert url == "http://test.com"
    assert title == "Test Article Title"
    assert len(paragraphs) == 2
    assert "National Highway Traffic Safety Administration" in paragraphs[0]
    assert "2.8 million Tesla vehicles" in paragraphs[1]
    # Footer content should be excluded
    assert not any("footer content" in para for para in paragraphs)

# Test that extract_and_filter_paragraphs filters by AI funding content
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_filters_ai_funding():
    # HTML content with AI funding keywords
    html_content = """
    <html>
        <head><title>AI Startup Raises $10M</title></head>
        <body>
            <h1>AI Startup Raises $10M</h1>
            <div class="single-post-content">
                <p>An artificial intelligence startup secured $10 million in Series A funding.</p>
                <p>The machine learning company raised funding from investors.</p>
            </div>
        </body>
    </html>
    """
    
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            return mock_response
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    semaphore = asyncio.Semaphore(1)
    
    url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
        mock_client, "http://test.com", semaphore
    )
    
    # Should extract paragraphs since content has both AI and funding keywords
    assert len(paragraphs) > 0
    assert title == "AI Startup Raises $10M"

# Test that extract_and_filter_paragraphs handles errors gracefully
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_handles_errors():
    # Create a mock AsyncClient that raises an error
    class MockAsyncClient:
        async def get(self, url, *args, **kwargs):
            raise Exception("Network error")
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_client = MockAsyncClient()
    semaphore = asyncio.Semaphore(1)
    
    # Should return empty results on error
    url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
        mock_client, "http://test.com", semaphore
    )
    
    assert url == "http://test.com"
    assert paragraphs == []
    assert title == ""

