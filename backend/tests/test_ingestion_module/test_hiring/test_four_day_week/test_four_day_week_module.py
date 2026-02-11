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

from ingestion_module.hiring.four_day_week.fetch import parse_rss, main

def test_parse_rss_valid_4day():
    """Test parsing of valid 4 Day Week RSS XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer</title>
                <link>https://4dayweek.io/remote-job/python-dev-123</link>
                <description>4 day week role.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Developer"
    assert jobs[0]["id"] == "python-dev-123"

@pytest.mark.asyncio
async def test_four_day_week_main_orchestration():
    """Test full orchestration for 4 Day Week."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Engineer</title>
                <link>https://4dayweek.io/remote-job/1</link>
                <description>Django work.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
                <title>Marketing Manager</title>
                <link>https://4dayweek.io/remote-job/2</link>
                <description>Growth roles.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_ai_results = {
        "company_name": ["Scale AI"],
        "job_roles": [["Backend Expert"]],
        "tags": [["Python", "4DayWeek"]]
    }

    with patch("ingestion_module.hiring.four_day_week.fetch.fetch_rss_content", return_value=xml_content):
        with patch("ingestion_module.hiring.four_day_week.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "4 Day Week"
            # Should filter out Marketing
            assert len(results["title"]) == 1
            assert "Python" in results["title"][0]
            assert results["company_name"][0] == "Scale AI"
