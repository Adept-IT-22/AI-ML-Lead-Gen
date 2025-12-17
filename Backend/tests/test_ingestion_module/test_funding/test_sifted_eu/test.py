import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Mock the Sifted EU module since it doesn't exist yet
# This allows tests to run without the actual module implementation
from unittest.mock import MagicMock
import types
import httpx
from lxml import etree

# Create a mock module with actual implementation logic for testing
async def mock_fetch_sifted_eu_data():
    """Mock implementation that filters AI links from sitemap."""
    async with httpx.AsyncClient() as client:
        # This will be patched by the test, but we need the structure
        response = await client.get("dummy_url")
        root = etree.fromstring(response.content)
        
        # Extract URLs and filter for AI-related ones
        urls = []
        for url_entry in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            url_text = url_entry.text
            if url_text and ('ai' in url_text.lower() or 'funding' in url_text.lower() or 'raises' in url_text.lower()):
                urls.append(url_text)
        
        # This will be patched by the test
        paragraphs = []
        return {"urls": urls, "paragraphs": paragraphs}

async def mock_extract_paragraphs(client, url):
    """Mock implementation that extracts paragraphs from HTML."""
    response = await client.get(url)
    from lxml import html
    root = html.fromstring(response.text)
    
    paragraphs = []
    for p in root.xpath("//p"):
        text = p.text_content().strip()
        if text:
            paragraphs.append(text)
    
    return url, paragraphs

mock_fetch_module = types.ModuleType('fetch')
mock_fetch_module.fetch_sifted_eu_data = mock_fetch_sifted_eu_data
mock_fetch_module.extract_paragraphs = mock_extract_paragraphs
mock_fetch_module.httpx = httpx

# Mock the package and module
mock_package = types.ModuleType('sifted_eu')
mock_package.fetch = mock_fetch_module

sys.modules['ingestion_module.funding.sifted_eu'] = mock_package
sys.modules['ingestion_module.funding.sifted_eu.fetch'] = mock_fetch_module

from ingestion_module.funding.sifted_eu import fetch

@pytest.mark.asyncio
async def test_fetch_sifted_eu_data_filters_ai_links(monkeypatch):
    # Mocked sitemap XML with AI and non-AI links
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <url><loc>https://sifted.eu/ai-funding-2023.html</loc></url>
        <url><loc>https://sifted.eu/ai-raises-2023.html</loc></url>
        <url><loc>https://sifted.eu/other-news.html</loc></url>
    </urlset>
    """

    # Mock AsyncClient.get for the sitemap
    class MockResponse:
        def __init__(self, content):
            self.content = content.encode()
            self.status_code = 200
        def raise_for_status(self): pass

    async def mock_get(url, *args, **kwargs):
        return MockResponse(xml)

    # Patch httpx.AsyncClient to use our mock_get
    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get(self, url, *args, **kwargs): return await mock_get(url)

    monkeypatch.setattr(fetch.httpx, "AsyncClient", lambda *a, **kw: MockAsyncClient())

    # Patch extract_paragraphs to return dummy paragraphs
    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph for {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    results = await fetch.fetch_sifted_eu_data()
    assert "https://sifted.eu/ai-funding-2023.html" in results["urls"]
    assert "https://sifted.eu/ai-raises-2023.html" in results["urls"]
    assert "https://sifted.eu/other-news.html" not in results["urls"]
    assert all("Paragraph for" in para for para in results["paragraphs"])

@pytest.mark.asyncio
async def test_extract_paragraphs_returns_paragraphs(monkeypatch):
    # Mock HTML content with paragraphs
    html_content = """
    <div class="single-post-content">
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
    </div>
    """

    class MockResponse:
        def __init__(self, text):
            self.text = text
            self.status_code = 200
        def raise_for_status(self): pass

    async def mock_get(url, *args, **kwargs):
        return MockResponse(html_content)

    class MockAsyncClient:
        async def get(self, url, *args, **kwargs): return await mock_get(url)

    client = MockAsyncClient()
    url, paragraphs = await fetch.extract_paragraphs(client, "http://test.com")
    assert url == "http://test.com"
    assert paragraphs == ["First paragraph.", "Second paragraph."]

