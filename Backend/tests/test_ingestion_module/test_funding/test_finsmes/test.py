import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
from ingestion_module.funding.finsmes import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Test that find_newest_sitemap returns the latest sitemap URL containing '-post-2.xml'
@pytest_asyncio.fixture
def mock_client():
    return MagicMock()

@pytest.mark.asyncio
async def test_find_newest_sitemap_returns_latest_url(mock_client):
    # Simulate XML with two sitemaps, one with -post-2.xml
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>https://www.finsmes.com/wp-sitemap-post-1.xml</loc></sitemap>
        <sitemap><loc>https://www.finsmes.com/wp-sitemap-post-2.xml</loc></sitemap>
    </sitemapindex>
    """
    mock_response = MagicMock()
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    # Patch fetch_sync to return the mocked response
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        url = await fetch_mod.find_newest_sitemap(mock_client, "dummy_url")
        assert url == "https://www.finsmes.com/wp-sitemap-post-2.xml"

# Test that fetch_ai_funding_article_links filters and returns only AI funding article links
@pytest.mark.asyncio
async def test_fetch_ai_funding_article_links_filters_ai_and_funding(mock_client):
    xml = """
        <urlset xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap:url><sitemap:loc>https://www.finsmes.com/adept-ai-funding-2023.html</sitemap:loc></sitemap:url>
            <sitemap:url><sitemap:loc>https://www.finsmes.com/not-adept-ai-raises-2023.html</sitemap:loc></sitemap:url>
            <sitemap:url><sitemap:loc>https://www.finsmes.com/other-news.html</sitemap:loc></sitemap:url>
        </urlset>

    """
    mock_response = MagicMock()
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    # Patch fetch_sync to return the mocked response
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        links = await fetch_mod.fetch_ai_funding_article_links(mock_client, "dummy_url")
        assert "https://www.finsmes.com/adept-ai-funding-2023.html" in links
        assert "https://www.finsmes.com/not-adept-ai-raises-2023.html" in links
        assert "https://www.finsmes.com/other-news.html" not in links

# Test that extract_paragraphs returns the correct paragraphs from HTML content
@pytest.mark.asyncio
async def test_extract_paragraphs_returns_paragraphs(mock_client):
    html_content = """
    <div class="tdb-block-inner td-fix-index">
        <p>Paragraph 1</p>
        <p>Paragraph 2</p>
    </div>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    # Patch fetch_sync to return the mocked HTML response
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        semaphore = asyncio.Semaphore(1)
        url, paragraphs = await fetch_mod.extract_paragraphs(mock_client, "http://test.com", semaphore)
        assert url == "http://test.com"
        assert paragraphs == ["Paragraph 1", "Paragraph 2"]

# Test that get_paragraphs returns empty results when given an empty URL list
@pytest.mark.asyncio
async def test_get_paragraphs_handles_empty_urls(mock_client):
    semaphore = asyncio.Semaphore(1)
    result = await fetch_mod.get_paragraphs(mock_client, [], semaphore)
    assert result == {"urls": [], "paragraphs": []}

# Test that get_paragraphs gathers results from multiple URLs using a monkeypatched extract_paragraphs
@pytest.mark.asyncio
async def test_get_paragraphs_gathers_results(monkeypatch, mock_client):
    urls = ["url1", "url2"]
    semaphore = asyncio.Semaphore(2)
    # Monkeypatch extract_paragraphs to return predictable results
    async def fake_extract(client, url, sem):
        return url, [f"Paragraph for {url}"]
    monkeypatch.setattr(fetch_mod, "extract_paragraphs", fake_extract)
    result = await fetch_mod.get_paragraphs(mock_client, urls, semaphore)
    assert set(result["urls"]) == set(urls)
    for para in result["paragraphs"]:
        assert "Paragraph for" in para