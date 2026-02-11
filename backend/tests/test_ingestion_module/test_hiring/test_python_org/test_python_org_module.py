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

from ingestion_module.hiring.python_org.fetch import parse_rss, main

def test_parse_rss_valid():
    """Test parsing of valid Python.org RSS XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Senior Python Dev</title>
                <link>https://www.python.org/jobs/123/</link>
                <description>We need you.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    jobs = parse_rss(xml_content)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Dev"
    assert jobs[0]["id"] == "123"

@pytest.mark.asyncio
async def test_python_org_main_orchestration():
    """Test full orchestration including filtering and mock AI."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Backend Engineer</title>
                <link>https://www.python.org/jobs/1/</link>
                <description>Django expert.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
                <title>Janitor</title>
                <link>https://www.python.org/jobs/2/</link>
                <description>Cleaning roles.</description>
                <pubDate>Thu, 08 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    mock_ai_results = {
        "company_name": ["Acme Corp"],
        "job_roles": [["Backend Expert"]],
        "tags": [["Python", "Django"]]
    }

    with patch("ingestion_module.hiring.python_org.fetch.fetch_rss_content", return_value=xml_content):
        with patch("ingestion_module.hiring.python_org.fetch.finalize_ai_extraction", return_value=mock_ai_results):
            results = await main()
            
            assert results is not None
            assert results["source"] == "Python.org"
            # Should filter out Janitor
            assert len(results["title"]) == 1
            assert "Python" in results["title"][0]
            assert results["company_name"][0] == "Acme Corp"
