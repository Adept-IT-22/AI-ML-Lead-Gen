"""
Pytest test cases for Jobspresso Jobs module.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
from ingestion_module.hiring.jobspresso import fetch as fetch_mod

@pytest.mark.asyncio
async def test_parse_rss_jobspresso():
    """Test parsing of Jobspresso RSS."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>DevOps Engineer</title>
                <link>https://jobspresso.co/job/devops</link>
                <guid>101</guid>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = fetch_mod.parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "DevOps Engineer"

@pytest.mark.asyncio
async def test_main_success_jobspresso():
    """Test Jobspresso main success."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>DevOps Engineer</title>
                <link>https://jobspresso.co/job/devops</link>
                <guid>101</guid>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = xml_content
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    extracted_data = {
        "article_id": ["101"],
        "article_link": ["https://jobspresso.co/job/devops"],
        "title": ["DevOps Engineer"],
    }
    
    async def mock_finalize(data):
        return extracted_data

    with patch('ingestion_module.hiring.jobspresso.fetch.httpx.AsyncClient', return_value=mock_client):
        with patch('ingestion_module.ai_extraction.extract_hiring_content.finalize_ai_extraction', side_effect=mock_finalize):
            result = await fetch_mod.main()
            
            assert result is not None
            assert result["source"] == "Jobspresso"
            assert len(result["link"]) == 1
