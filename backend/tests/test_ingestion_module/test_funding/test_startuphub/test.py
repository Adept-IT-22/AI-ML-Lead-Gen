import pytest
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from ingestion_module.funding.startup_hub import fetch

@pytest.mark.asyncio
async def test_fetch_startuphub_data_filters_ai_funding_links(monkeypatch):
    # Mocked sitemap XML with AI/funding and non-matching links
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://www.startuphub.ai/2025/11/ai-startup-raises-10m</loc>
            <n:publication_date>2025-11-06</n:publication_date>
        </url>
        <url>
            <loc>https://www.startuphub.ai/2025/11/other-news</loc>
            <n:publication_date>2025-11-06</n:publication_date>
        </url>
    </urlset>
    """

    class MockResponse:
        def __init__(self, content, headers=None):
            self.content = content.encode()
            self.status_code = 200
            self.headers = headers or {"Content-Type": "application/xml"}
        def raise_for_status(self): pass

    async def mock_get(url, *args, **kwargs):
        return MockResponse(xml, headers={"Content-Type": "application/xml"})

    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get(self, url, *args, **kwargs): return await mock_get(url)

    monkeypatch.setattr(fetch.httpx, "AsyncClient", lambda *a, **kw: MockAsyncClient())

    async def fake_extract_paragraphs(client, url):
        return url, [f"Paragraph for {url}"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    results = await fetch.fetch_startuphub_data()
    assert "https://www.startuphub.ai/2025/11/ai-startup-raises-10m" in results["urls"]
    assert "https://www.startuphub.ai/2025/11/other-news" not in results["urls"]
    assert all("Paragraph for" in para for para in results["paragraphs"])

@pytest.mark.asyncio
async def test_extract_paragraphs_returns_paragraphs(monkeypatch):
    html_content = """
    <div class="infinity-article-content">
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
    </div>
    """

    class MockResponse:
        def __init__(self, text, headers=None):
            self.text = text
            self.status_code = 200
            self.headers = headers or {"Content-Type": "text/html"}
        def raise_for_status(self): pass

    async def mock_get(url, *args, **kwargs):
        return MockResponse(html_content, headers={"Content-Type": "text/html"})

    class MockAsyncClient:
        async def get(self, url, *args, **kwargs): return await mock_get(url)

    client = MockAsyncClient()
    url, paragraphs = await fetch.extract_paragraphs(client, "http://test.com")
    assert url == "http://test.com"
    assert paragraphs == ["First paragraph.", "Second paragraph."]

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_integration_with_ai_extraction(monkeypatch):
    # Fake sitemap with one valid AI+funding link
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://www.startuphub.ai/2025/11/ai-startup-raises-10m</loc>
            <n:publication_date>2025-11-06</n:publication_date>
        </url>
    </urlset>
    """

    class MockResponse:
        def __init__(self, content, headers=None):
            self.content = content.encode()
            self.status_code = 200
            self.headers = headers or {"Content-Type": "application/xml"}
        def raise_for_status(self): pass

    async def mock_get(url, *args, **kwargs):
        return MockResponse(xml, headers={"Content-Type": "application/xml"})

    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get(self, url, *args, **kwargs): return await mock_get(url)

    monkeypatch.setattr(fetch.httpx, "AsyncClient", lambda *a, **kw: MockAsyncClient())

    async def fake_extract_paragraphs(client, url):
        return url, ["AI funding paragraph"]
    monkeypatch.setattr(fetch, "extract_paragraphs", fake_extract_paragraphs)

    # Patch finalize_ai_extraction to return fake AI results with correct keys
    fake_ai_result = {
        "company_name": ["TestAI"],
        "amount_raised": ["$10M"],
        "currency": ["USD"],
        "title": ["AI startup raises funding"],
        "link": ["https://www.startuphub.ai/2025/11/ai-startup-raises-10m"],
        "article_date": ["2025-11-06"]
    }

    with patch("ingestion_module.funding.startup_hub.fetch.finalize_ai_extraction", return_value=fake_ai_result):
        result = await fetch.main()

    assert result is not None
    assert "TestAI" in result["company_name"]
    assert "$10M" in result["amount_raised"]
    assert "startuphub.ai" in result["link"][0]