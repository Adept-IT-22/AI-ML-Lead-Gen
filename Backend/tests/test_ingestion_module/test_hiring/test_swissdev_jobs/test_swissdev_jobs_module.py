import pytest
import sys
import os
from unittest.mock import patch

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "Backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.environ["GEMINI_API_KEY"] = "mock_key"

from ingestion_module.hiring.swissdev_jobs.fetch import parse_rss, main

def test_parse_rss_valid():
    """Test parsing of valid SwissDev Jobs RSS XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Developer @ SwissBank</title>
                <link>https://swissdevjobs.ch/jobs/python-dev-123</link>
                <description>Zurich role.</description>
                <pubDate>Thu, 09 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Developer @ SwissBank"

@pytest.mark.asyncio
async def test_main_orchestration():
    """Test full orchestration for SwissDev Jobs."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Dev</title>
                <link>https://swissdevjobs.ch/job/1</link>
                <description>Django.</description>
                <pubDate>Thu, 09 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_ai = {"company_name": ["Swiss Co"], "job_roles": [["Backend"]], "tags": [["Python"]]}

    with patch("ingestion_module.hiring.swissdev_jobs.fetch.fetch_rss_content", return_value=xml_content):
        with patch("ingestion_module.hiring.swissdev_jobs.fetch.finalize_ai_extraction", return_value=mock_ai):
            results = await main()
            assert results["source"] == "SwissDev Jobs"
            assert len(results["title"]) == 1
