import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

# Mock the AI extraction module before importing fetch to avoid loading Google AI model
from unittest.mock import MagicMock
sys.modules['ingestion_module.ai_extraction.extract_funding_content'] = MagicMock()
sys.modules['ingestion_module.ai_extraction.extract_funding_content'].finalize_ai_extraction = MagicMock()  # type: ignore

# Mock cloudscraper before importing fetch
sys.modules['cloudscraper'] = MagicMock()

from ingestion_module.funding.pitchbook import fetch as fetch_mod

import pytest_asyncio
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import gzip

# Test that parse_sitemap_index returns relevant sitemap URLs
@pytest_asyncio.fixture
def mock_scraper_client():
    return MagicMock()

@pytest.mark.asyncio
async def test_parse_sitemap_index_returns_relevant_urls(mock_scraper_client):
    # Simulate XML with sitemaps, some matching relevant patterns
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>https://pitchbook.com/sitemap-press-release.xml.gz</loc></sitemap>
        <sitemap><loc>https://pitchbook.com/sitemap-na-newsletter.xml.gz</loc></sitemap>
        <sitemap><loc>https://pitchbook.com/sitemap-other.xml.gz</loc></sitemap>
    </sitemapindex>
    """
    mock_response = MagicMock()
    mock_response.content = xml.encode()
    mock_response.raise_for_status = MagicMock()
    
    # Patch fetch_sync to return the mocked response
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        urls = await fetch_mod.parse_sitemap_index(mock_scraper_client, "dummy_url")
        assert "https://pitchbook.com/sitemap-press-release.xml.gz" in urls
        assert "https://pitchbook.com/sitemap-na-newsletter.xml.gz" in urls
        assert "https://pitchbook.com/sitemap-other.xml.gz" not in urls

# Test that fetch_and_decompress_gz decompresses gzip content
@pytest.mark.asyncio
async def test_fetch_and_decompress_gz_decompresses_content(mock_scraper_client):
    # Create sample gzip content
    original_content = b"<urlset><url><loc>https://test.com</loc></url></urlset>"
    gzipped_content = gzip.compress(original_content)
    
    mock_response = MagicMock()
    mock_response.content = gzipped_content
    mock_response.raise_for_status = MagicMock()
    
    # Patch fetch_gz_with_scraper to return the mocked response
    with patch.object(fetch_mod, "fetch_gz_with_scraper", return_value=gzipped_content):
        decompressed = await fetch_mod.fetch_and_decompress_gz(mock_scraper_client, "dummy_url")
        assert decompressed == original_content

# Test that parse_decompressed_sitemap extracts URLs and dates
@pytest.mark.asyncio
async def test_parse_decompressed_sitemap_extracts_urls_and_dates():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://pitchbook.com/article1</loc>
            <lastmod>2025-11-05T07:24:35.003+00:00</lastmod>
        </url>
        <url>
            <loc>https://pitchbook.com/article2</loc>
            <lastmod>2025-10-01T00:00:00.000+00:00</lastmod>
        </url>
    </urlset>
    """
    articles = await fetch_mod.parse_decompressed_sitemap(xml.encode())
    assert len(articles) == 2
    assert articles[0]['url'] == "https://pitchbook.com/article1"
    assert articles[0]['lastmod'] == "2025-11-05T07:24:35.003+00:00"
    assert articles[1]['url'] == "https://pitchbook.com/article2"
    assert articles[1]['lastmod'] == "2025-10-01T00:00:00.000+00:00"

# Test that is_ai_funding_related_content filters correctly
def test_is_ai_funding_related_content_requires_both_ai_and_funding():
    # Should return True for AI + funding
    assert fetch_mod.is_ai_funding_related_content(
        "AI Company", "raises $10 million in Series A"
    )
    
    # Should return False for only AI
    assert not fetch_mod.is_ai_funding_related_content(
        "AI Company", "releases new product"
    )
    
    # Should return False for only funding
    assert not fetch_mod.is_ai_funding_related_content(
        "Tech Company", "raises $10 million"
    )
    
    # Should return True for various AI keywords
    assert fetch_mod.is_ai_funding_related_content(
        "Machine Learning Startup", "secures funding"
    )
    
    # Should return True for various funding keywords
    assert fetch_mod.is_ai_funding_related_content(
        "AI Startup", "closes Series B round"
    )

# Test that is_within_last_two_months filters dates correctly
def test_is_within_last_two_months_filters_recent_dates():
    # Recent date (within 2 months)
    recent_date = (datetime.now() - timedelta(days=30)).isoformat()
    assert fetch_mod.is_within_last_two_months(recent_date)
    
    # Old date (more than 2 months ago)
    old_date = (datetime.now() - timedelta(days=90)).isoformat()
    assert not fetch_mod.is_within_last_two_months(old_date)
    
    # Today's date
    today_date = datetime.now().isoformat()
    assert fetch_mod.is_within_last_two_months(today_date)
    
    # None should return True (fallback)
    assert fetch_mod.is_within_last_two_months(None)
    
    # Invalid date should return True (fallback)
    assert fetch_mod.is_within_last_two_months("invalid-date")

# Test that extract_and_filter_paragraphs returns paragraphs from HTML
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_returns_paragraphs(mock_scraper_client):
    # HTML content with newsletter format (span with br tags)
    html_content = """
    <div class="article__content">
        <div class="nb-content">
            <span>
                <b>Company A</b> raised $10 million in Series A.<br><br>
                <b>Company B</b> secured funding from investors.<br><br>
            </span>
        </div>
    </div>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    
    # Patch fetch_sync to return the mocked response
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        semaphore = asyncio.Semaphore(1)
        url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
            mock_scraper_client, "http://test.com", semaphore
        )
        assert url == "http://test.com"
        assert len(paragraphs) > 0
        assert any("Company A" in p or "Company B" in p for p in paragraphs)

# Test that extract_and_filter_paragraphs handles standard p tags
@pytest.mark.asyncio
async def test_extract_and_filter_paragraphs_handles_p_tags(mock_scraper_client):
    html_content = """
    <article>
        <p>First paragraph with funding information that is long enough to pass the minimum character requirement of fifty characters or more.</p>
        <p>Second paragraph with AI content that is also long enough to meet the minimum character requirement for paragraph extraction.</p>
    </article>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(fetch_mod, "fetch_sync", return_value=mock_response):
        semaphore = asyncio.Semaphore(1)
        url, paragraphs, title = await fetch_mod.extract_and_filter_paragraphs(
            mock_scraper_client, "http://test.com", semaphore
        )
        assert url == "http://test.com"
        assert len(paragraphs) >= 2
        assert "First paragraph" in paragraphs[0] or any("First paragraph" in p for p in paragraphs)
        assert "Second paragraph" in paragraphs[1] or any("Second paragraph" in p for p in paragraphs)

# Test that fetch_pitchbook_data returns empty results when no sitemaps found
@pytest.mark.asyncio
async def test_fetch_pitchbook_data_handles_no_sitemaps(monkeypatch):
    # Mock parse_sitemap_index to return empty list
    async def mock_parse_sitemap_index(*args, **kwargs):
        return []
    
    monkeypatch.setattr(fetch_mod, "parse_sitemap_index", mock_parse_sitemap_index)
    
    # Mock cloudscraper.create_scraper
    mock_scraper = MagicMock()
    with patch.object(fetch_mod.cloudscraper, "create_scraper", return_value=mock_scraper):
        results = await fetch_mod.fetch_pitchbook_data()
        assert results == {"urls": [], "paragraphs": []}

# Test that fetch_pitchbook_data filters by date and content
@pytest.mark.asyncio
async def test_fetch_pitchbook_data_filters_correctly(monkeypatch):
    # Mock successful sitemap parsing
    async def mock_parse_sitemap_index(*args, **kwargs):
        return ["https://pitchbook.com/sitemap-press-release.xml.gz"]
    
    # Mock decompression and parsing
    async def mock_fetch_and_decompress_gz(*args, **kwargs):
        xml = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://pitchbook.com/article1</loc>
                <lastmod>2025-11-05T07:24:35.003+00:00</lastmod>
            </url>
        </urlset>
        """
        return xml.encode()
    
    # Mock paragraph extraction
    async def mock_extract_and_filter_paragraphs(client, url, semaphore):
        return url, ["AI company raises $10 million in funding"], "AI Funding News"
    
    monkeypatch.setattr(fetch_mod, "parse_sitemap_index", mock_parse_sitemap_index)
    monkeypatch.setattr(fetch_mod, "fetch_and_decompress_gz", mock_fetch_and_decompress_gz)
    monkeypatch.setattr(fetch_mod, "extract_and_filter_paragraphs", mock_extract_and_filter_paragraphs)
    
    mock_scraper = MagicMock()
    with patch.object(fetch_mod.cloudscraper, "create_scraper", return_value=mock_scraper):
        results = await fetch_mod.fetch_pitchbook_data()
        assert "urls" in results
        assert "paragraphs" in results
        assert len(results["urls"]) > 0 or len(results["paragraphs"]) > 0

