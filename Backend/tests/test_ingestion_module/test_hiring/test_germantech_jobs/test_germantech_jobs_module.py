import pytest
import sys
import os
from unittest.mock import patch

# Add Backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock environment variable
os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.germantech_jobs.fetch import parse_rss, main

def test_parse_rss_valid_gtj():
    """Test parsing of valid GermanTech Jobs RSS XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer @ BerlinTech</title>
                <link>https://germantechjobs.de/job/python-dev-123</link>
                <description>Remote role in Germany.</description>
                <pubDate>Thu, 09 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Developer @ BerlinTech"
    assert jobs[0]["id"] == "python-dev-123"

@pytest.mark.asyncio
async def test_gtj_main_orchestration():
    """Test full orchestration for GermanTech Jobs."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Dev</title>
                <link>https://germantechjobs.de/job/1</link>
                <description>Django work.</description>
                <pubDate>Thu, 09 Jan 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
                <title>Accountant</title>
                <link>https://germantechjobs.de/job/2</link>
                <description>Finance role.</description>
                <pubDate>Thu, 09 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_ai_results = {
        "company_name": ["BerlinTech"],
        "job_roles": [["Backend Expert"]],
        "tags": [["Python", "Remote"]]
    }

    with patch("ingestion_module.hiring.germantech_jobs.fetch.fetch_rss_content", return_value=xml_content):
        with patch("ingestion_module.hiring.germantech_jobs.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "GermanTech Jobs"
            # Should filter out Accountant
            assert len(results["title"]) == 1
            assert "Python" in results["title"][0]
            assert results["company_name"][0] == "BerlinTech"
