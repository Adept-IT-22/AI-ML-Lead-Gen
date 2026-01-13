import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add Backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.djinni.fetch import parse_rss, main

def test_parse_rss_valid_djinni():
    """Test parsing of valid Djinni RSS XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer</title>
                <link>https://djinni.co/jobs/12345/</link>
                <description>Remote role.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Developer"
    assert jobs[0]["id"] == "12345"

@pytest.mark.asyncio
async def test_djinni_main_orchestration():
    """Test full orchestration for Djinni."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Engineer</title>
                <link>https://djinni.co/jobs/1</link>
                <description>Django work.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
                <title>Office Manager</title>
                <link>https://djinni.co/jobs/2</link>
                <description>Admin role.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_ai_results = {
        "company_name": ["Djinni Client"],
        "job_roles": [["Backend Expert"]],
        "tags": [["Python", "Remote"]]
    }

    with patch("ingestion_module.hiring.djinni.fetch.fetch_rss_content", return_value=xml_content):
        with patch("ingestion_module.hiring.djinni.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "Djinni"
            # Should filter out Office Manager
            assert len(results["title"]) == 1
            assert "Python" in results["title"][0]
            assert results["company_name"][0] == "Djinni Client"
