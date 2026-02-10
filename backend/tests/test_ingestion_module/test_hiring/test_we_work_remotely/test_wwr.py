"""
Pytest test cases for We Work Remotely Jobs module.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os


# Add Backend to path
# Current file is in Backend/tests/test_ingestion_module/test_hiring/test_we_work_remotely/
# We need to add 'Backend' to sys.path so 'ingestion_module' can be imported
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable BEFORE importing modules that might check it
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.we_work_remotely import fetch as fetch_mod

@pytest.mark.asyncio
async def test_parse_rss_success():
    """Test parsing of valid RSS feed."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer</title>
                <link>https://weworkremotely.com/job/1</link>
                <description>Great job</description>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
                <guid>1</guid>
            </item>
            <item>
                <title>Marketing Manager</title>
                <link>https://weworkremotely.com/job/2</link>
                <description>Marketing job</description>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
                <guid>2</guid>
            </item>
        </channel>
    </rss>
    """
    
    jobs = fetch_mod.parse_rss(xml_content)
    assert len(jobs) == 2
    assert jobs[0]["title"] == "Senior Python Developer"
    assert jobs[0]["url"] == "https://weworkremotely.com/job/1"
    assert jobs[1]["title"] == "Marketing Manager"

@pytest.mark.asyncio
async def test_main_keywords_filtering_success():
    """Test that main function filters jobs based on keywords."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer</title>
                <link>https://weworkremotely.com/job/1</link>
                <description>Python django job</description>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
                <guid>1</guid>
            </item>
            <item>
                <title>Chef</title>
                <link>https://weworkremotely.com/job/2</link>
                <description>Cooking job</description>
                <pubDate>Mon, 06 Jan 2026 10:00:00 +0000</pubDate>
                <guid>2</guid>
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
        "article_id": ["1"],
        "article_link": ["https://weworkremotely.com/job/1"],
        "title": ["Senior Python Developer"],
        "company_name": ["Unknown"],
    }
    
    async def mock_finalize(data):
        return extracted_data

    with patch('ingestion_module.hiring.we_work_remotely.fetch.httpx.AsyncClient', return_value=mock_client):
        with patch('ingestion_module.ai_extraction.extract_hiring_content.finalize_ai_extraction', side_effect=mock_finalize):
            result = await fetch_mod.main()
            
            assert result is not None
            assert result["source"] == "WeWorkRemotely"
            # Should have filtered out Chef (assuming 'python' is a keyword and 'chef' is not)
            # Checking length of titles/links
            assert len(result["link"]) == 1
            assert result["link"][0] == "https://weworkremotely.com/job/1"
