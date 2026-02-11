import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from ingestion_module.funding.tech_eu import fetch

@pytest.mark.asyncio
async def test_fetch_tech_eu_data_filters_ai_links(monkeypatch):
    # Mocked sitemap XML with AI and non-AI links
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <url><loc>https://tech.eu/ai-funding-2023.html</loc></url>
        <url><loc>https://tech.eu/ai-raises-2023.html</loc></url>
        <url><loc>https://tech.eu/other-news.html</loc></url>
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

    results = await fetch.fetch_tech_eu_data()
    assert "https://tech.eu/ai-funding-2023.html" in results["urls"]
    assert "https://tech.eu/ai-raises-2023.html" in results["urls"]
    assert "https://tech.eu/other-news.html" not in results["urls"]
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