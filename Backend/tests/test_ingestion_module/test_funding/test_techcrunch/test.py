import pytest
import pytest_asyncio
import httpx
import json
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from ingestion_module.funding.techcrunch import fetch

@pytest_asyncio.fixture
def mock_client(monkeypatch):
    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get(self, url, *args, **kwargs): return self.mock_get(url)
        def set_mock_get(self, func): self.mock_get = func

    client = MockAsyncClient()
    monkeypatch.setattr(fetch.httpx, "AsyncClient", lambda *a, **kw: client)
    return client

@pytest.mark.asyncio
async def test_main_success_with_data(monkeypatch, mock_client):
    # Mock sitemap and article responses
    sitemap_xml = b"""
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://techcrunch.com/2025/08/04/company-ai-raises-funding/</loc>
            <news:news>
                <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                <news:title>Company AI Raises Funding</news:title>
            </news:news>
        </url>
    </urlset>
    """
    article_html = b"""
    <html><body><p class="wp-block-paragraph">Test paragraph.</p></body></html>
    """

    article_response = MagicMock(
        content=article_html,
        text=article_html.decode(),  # Add this line!
        status_code=200,
        raise_for_status=lambda: None
    )

    responses = [
        MagicMock(content=sitemap_xml, status_code=200, raise_for_status=lambda: None),
        article_response
    ]
    mock_client.set_mock_get(lambda url: responses.pop(0))

    # Patch finalize_ai_extraction
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(return_value={
        "title": ["Test Title"],
        "link": ["https://techcrunch.com/2025/08/04/company-ai-raises-funding/"],
        "article_date": ["2025-08-04"],
        "company_name": ["Test Co"],
        "tags": [["AI", "Funding"]]
    }))

    # Patch aiofiles.open to a mock
    mock_file = MagicMock()
    class DummyAiofiles:
        async def __aenter__(self): return mock_file
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(fetch.aiofiles, "open", lambda *a, **kw: DummyAiofiles())

    result = await fetch.main()
    print(f"RESULT IS : {result}")
    assert result is not None
    assert result["source"] == "TechCrunch"
    assert "Test Title" in result["title"]
    assert "https://techcrunch.com/2025/08/04/company-ai-raises-funding/" in result["link"]

@pytest.mark.asyncio
async def test_main_no_ai_urls(monkeypatch, mock_client):
    sitemap_xml = b"""
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://techcrunch.com/2025/08/04/company-no-ai-no-funding/</loc>
            <news:news>
                <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                <news:title>Company No AI No Funding</news:title>
            </news:news>
        </url>
    </urlset>
    """
    # Only one response: the sitemap
    mock_client.set_mock_get(lambda url: MagicMock(content=sitemap_xml, status_code=200, raise_for_status=lambda: None))

    # Patch finalize_ai_extraction to return empty dict
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(return_value={}))

    # Patch aiofiles.open to a dummy async context manager
    mock_file = MagicMock()
    class DummyAiofiles:
        async def __aenter__(self): return mock_file
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(fetch.aiofiles, "open", lambda *a, **kw: DummyAiofiles())

    await fetch.main()
    # Should not call file write
    assert not mock_file.writelines.called
    fetch.finalize_ai_extraction.assert_called_once()

@pytest.mark.asyncio
async def test_main_llm_extraction_failure(monkeypatch, mock_client):
    # Mock sitemap and article responses
    sitemap_xml = b"""
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
        <url>
            <loc>https://techcrunch.com/2025/08/04/company-ai-raises-funding/</loc>
            <news:news>
                <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                <news:title>Company AI Raises Funding</news:title>
            </news:news>
        </url>
    </urlset>
    """
    article_html = b"""
    <html><body><p class="wp-block-paragraph">Test paragraph.</p></body></html>
    """

    article_response = MagicMock(
        content=article_html,
        text=article_html.decode(),  # Add this line!
        status_code=200,
        raise_for_status=lambda: None
    )

    responses = [MagicMock(content=sitemap_xml, status_code=200, raise_for_status=lambda: None),
                 article_response]
    mock_client.set_mock_get(lambda url: responses.pop(0))

    # Patch finalize_ai_extraction to raise
    monkeypatch.setattr(fetch, "finalize_ai_extraction", AsyncMock(side_effect=Exception("LLM API error")))
    monkeypatch.setattr(fetch.aiofiles, "open", MagicMock())

    await fetch.main()
    fetch.aiofiles.open.assert_not_called()
    fetch.finalize_ai_extraction.assert_called_once()