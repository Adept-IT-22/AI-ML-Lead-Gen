"""
Pytest test cases for Hacker News "Who is Hiring" module.
Tests RSS feed parsing, date filtering, comment fetching, and job extraction.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
from ingestion_module.hiring.hacker_news import fetch as fetch_mod

@pytest_asyncio.fixture
def mock_client():
    """Create a mock httpx.AsyncClient."""
    return MagicMock()

@pytest.mark.asyncio
async def test_is_within_last_month_recent_date():
    """Test that recent dates (within 1 month) return True."""
    recent_date = datetime.now(timezone.utc) - timedelta(days=15)
    rfc_date = recent_date.strftime("%a, %d %b %Y %H:%M:%S %z")
    
    result = fetch_mod.is_within_last_month(rfc_date)
    assert result

@pytest.mark.asyncio
async def test_is_within_last_month_old_date():
    """Test that old dates (beyond 1 month) return False."""
    old_date = datetime.now(timezone.utc) - timedelta(days=45)
    rfc_date = old_date.strftime("%a, %d %b %Y %H:%M:%S %z")
    
    result = fetch_mod.is_within_last_month(rfc_date)
    assert not result

@pytest.mark.asyncio
async def test_is_within_last_month_invalid_date():
    """Test that invalid dates return False."""
    result = fetch_mod.is_within_last_month("invalid date")
    assert not result

@pytest.mark.asyncio
async def test_is_within_last_month_none():
    """Test that None date returns False."""
    result = fetch_mod.is_within_last_month(None)
    assert not result

@pytest.mark.asyncio
async def test_fetch_who_is_hiring_threads_filters_correctly(mock_client):
    """Test that API-based fetching filters for 'Who is Hiring' threads."""
    # Mock user data
    recent_date = datetime.now(timezone.utc) - timedelta(days=15)  # Within last month
    user_data = {
        "id": "whoishiring",
        "submitted": [12345678, 87654321]  # Two thread IDs
    }
    
    # Mock thread data - one "Who is Hiring" and one other
    who_is_hiring_thread = {
        "id": 12345678,
        "title": "Ask HN: Who is hiring? (November 2025)",
        "time": int(recent_date.timestamp()),
        "type": "story"
    }
    
    other_thread = {
        "id": 87654321,
        "title": "Some other post",
        "time": int(recent_date.timestamp()),
        "type": "story"
    }
    
    async def mock_get(url, **kwargs):
        mock_response = MagicMock()
        if "user/whoishiring" in url:
            mock_response.json = lambda: user_data
        elif "item/12345678" in url:
            mock_response.json = lambda: who_is_hiring_thread
        elif "item/87654321" in url:
            mock_response.json = lambda: other_thread
        mock_response.raise_for_status = lambda: None
        return mock_response
    
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch('ingestion_module.hiring.hacker_news.fetch.get_header', return_value={}):
        threads = await fetch_mod.fetch_who_is_hiring_threads(mock_client)
        
        assert len(threads) == 1
        assert threads[0]['id'] == '12345678'
        assert 'Who is hiring' in threads[0]['title']

@pytest.mark.asyncio
async def test_fetch_who_is_hiring_threads_filters_by_date(mock_client):
    """Test that API-based fetching filters threads by date (last month)."""
    # Create mock data with old and recent threads
    recent_date = datetime.now(timezone.utc) - timedelta(days=15)  # Within last month
    old_date = datetime.now(timezone.utc) - timedelta(days=45)  # Older than 1 month
    
    user_data = {
        "id": "whoishiring",
        "submitted": [12345678, 87654321]  # Two thread IDs
    }
    
    recent_thread = {
        "id": 12345678,
        "title": "Ask HN: Who is hiring? (November 2025)",
        "time": int(recent_date.timestamp()),
        "type": "story"
    }
    
    old_thread = {
        "id": 87654321,
        "title": "Ask HN: Who is hiring? (August 2025)",
        "time": int(old_date.timestamp()),
        "type": "story"
    }
    
    async def mock_get(url, **kwargs):
        mock_response = MagicMock()
        if "user/whoishiring" in url:
            mock_response.json = lambda: user_data
        elif "item/12345678" in url:
            mock_response.json = lambda: recent_thread
        elif "item/87654321" in url:
            mock_response.json = lambda: old_thread
        mock_response.raise_for_status = lambda: None
        return mock_response
    
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch('ingestion_module.hiring.hacker_news.fetch.get_header', return_value={}):
        threads = await fetch_mod.fetch_who_is_hiring_threads(mock_client)
        
        # Should only include the recent thread
        assert len(threads) == 1
        assert threads[0]['id'] == '12345678'

@pytest.mark.asyncio
async def test_fetch_thread_comments_returns_comments(mock_client):
    """Test that thread comments are fetched correctly."""
    thread_id = "12345678"
    
    # Mock thread data with kids (comment IDs)
    thread_data = {
        "id": int(thread_id),
        "kids": [111, 222, 333],
        "type": "story"
    }
    
    # Mock comment data
    comment_data = {
        "id": 111,
        "type": "comment",
        "text": "We're hiring software engineers at TechCorp!"
    }
    
    # Mock API responses
    mock_thread_response = MagicMock()
    mock_thread_response.json.return_value = thread_data
    mock_thread_response.raise_for_status = MagicMock()
    
    mock_comment_response = MagicMock()
    mock_comment_response.json.return_value = comment_data
    mock_comment_response.raise_for_status = MagicMock()
    
    # Setup client to return different responses for thread and comments
    async def mock_get(url, **kwargs):
        
        if f"item/{thread_id}" in url:
            return mock_thread_response
        else:
            return mock_comment_response
    
    mock_client.get = AsyncMock(side_effect=mock_get)
    
    comments = await fetch_mod.fetch_thread_comments(mock_client, thread_id)
    
    assert len(comments) == 3  # Should fetch all 3 comments

@pytest.mark.asyncio
async def test_is_tech_related_job_filters_correctly():
    """Test that tech-related job filtering works correctly."""
    # Tech-related job posting
    tech_job = "We're hiring software engineers and developers. Python, JavaScript, React."
    assert fetch_mod.is_tech_related_job(tech_job)
    
    # Non-tech job posting
    non_tech_job = "We're hiring sales representatives and marketing managers."
    assert not fetch_mod.is_tech_related_job(non_tech_job)
    
    # Empty text
    assert not fetch_mod.is_tech_related_job("")
    assert not fetch_mod.is_tech_related_job(None)

@pytest.mark.asyncio
async def test_extract_job_postings_filters_tech_jobs():
    """Test that job postings are extracted and filtered for tech jobs."""
    comments = [
        {
            "id": 111,
            "text": "We're hiring software engineers! Python, React, AWS.",
            "type": "comment"
        },
        {
            "id": 222,
            "text": "We're hiring sales managers for our retail division.",
            "type": "comment"
        },
        {
            "id": 333,
            "text": "Looking for DevOps engineers and SREs. Kubernetes experience required.",
            "type": "comment"
        }
    ]
    
    job_postings = fetch_mod.extract_job_postings(comments, "12345678", "https://news.ycombinator.com/item?id=12345678")
    
    # Should only include tech-related jobs (111 and 333, not 222)
    assert len(job_postings["ids"]) == 2
    assert "111" in job_postings["ids"]
    assert "333" in job_postings["ids"]
    assert "222" not in job_postings["ids"]

@pytest.mark.asyncio
async def test_main_success_with_mocked_data(monkeypatch):
    """Test the main function with mocked data."""
    # Mock user data (whoishiring user's submissions)
    recent_date = datetime.now(timezone.utc) - timedelta(days=15)  # Within last month
    user_data = {
        "id": "whoishiring",
        "submitted": [12345678, 12345679]  # Two thread IDs
    }
    
    # Mock thread data (submission items)
    thread_data = {
        "id": 12345678,
        "title": "Ask HN: Who is hiring? (November 2025)",
        "time": int(recent_date.timestamp()),
        "kids": [111, 222],
        "type": "story"
    }
    
    # Mock comments
    comment_data = {
        "id": 111,
        "type": "comment",
        "text": "We're hiring software engineers at TechCorp! Python, React."
    }
    
    # Mock responses
    async def mock_get(url, **kwargs):
        mock_response = MagicMock()
        if "user/whoishiring" in url:
            # Make json() return the data directly (not a coroutine)
            mock_response.json = lambda: user_data
        elif "item/12345678" in url:
            mock_response.json = lambda: thread_data
        elif "item/111" in url:
            mock_response.json = lambda: comment_data
        else:
            # Default for other item IDs
            mock_response.json = lambda: {"id": 222, "type": "comment", "text": "Another job posting"}
        mock_response.raise_for_status = lambda: None  # Not a coroutine, just a no-op
        return mock_response
    
    # Mock extracted data from AI
    extracted_data = {
        "article_id": ["111"],
        "article_title": ["Software Engineer at TechCorp"],
        "company_name": ["TechCorp"],
        "job_roles": [["software engineer"]],
        "city": ["San Francisco"],
        "country": ["USA"]
    }
    
    # Setup mocks - httpx.AsyncClient is used as a context manager
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    async def mock_finalize_ai_extraction(data):
        return extracted_data
    
    with patch('ingestion_module.hiring.hacker_news.fetch.get_header', return_value={}):
        # Mock AsyncClient to return our mock client when used as context manager
        mock_async_client_class = MagicMock(return_value=mock_client)
        with patch('ingestion_module.hiring.hacker_news.fetch.httpx.AsyncClient', mock_async_client_class):
            # Mock the module at the point where it's imported
            with patch('ingestion_module.ai_extraction.extract_hiring_content.finalize_ai_extraction', new=mock_finalize_ai_extraction):
                result = await fetch_mod.main()
            
            assert result is not None
            assert result["source"] == "HackerNews"
            assert "TechCorp" in result["company_name"]
            assert len(result["link"]) > 0

@pytest.mark.asyncio
async def test_main_no_threads_found(monkeypatch):
    """Test main function when no threads are found."""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Some other post</title>
                <link>https://news.ycombinator.com/item?id=87654321</link>
                <pubDate>Mon, 03 Nov 2025 12:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    async def mock_get(url):
        mock_response = MagicMock()
        mock_response.content = rss_xml.encode('utf-8')
        mock_response.raise_for_status = MagicMock()
        return mock_response
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    
    with patch('ingestion_module.hiring.hacker_news.fetch.get_header', return_value={}):
        with patch('ingestion_module.hiring.hacker_news.fetch.httpx.AsyncClient', return_value=mock_client):
            result = await fetch_mod.main()
            
            assert result == {}

@pytest.mark.asyncio
async def test_main_no_tech_jobs_found(monkeypatch):
    """Test main function when no tech-related jobs are found."""
    recent_date = datetime.now(timezone.utc) - timedelta(days=30)
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Ask HN: Who is hiring? (November 2025)</title>
                <link>https://news.ycombinator.com/item?id=12345678</link>
                <pubDate>{recent_date.strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    thread_data = {
        "id": 12345678,
        "kids": [111],
        "type": "story"
    }
    
    # Non-tech comment
    comment_data = {
        "id": 111,
        "type": "comment",
        "text": "We're hiring sales managers and marketing coordinators."
    }
    
    async def mock_get(url, **kwargs):
        mock_response = MagicMock()
        if "rss" in url:
            mock_response.content = rss_xml.encode('utf-8')
        elif "item/12345678" in url:
            mock_response.json.return_value = thread_data
        else:
            mock_response.json.return_value = comment_data
        mock_response.raise_for_status = MagicMock()
        return mock_response
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    
    with patch('ingestion_module.hiring.hacker_news.fetch.get_header', return_value={}):
        with patch('ingestion_module.hiring.hacker_news.fetch.httpx.AsyncClient', return_value=mock_client):
            result = await fetch_mod.main()
            
            assert result == {}
