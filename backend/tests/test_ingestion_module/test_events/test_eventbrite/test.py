import pytest
from unittest.mock import AsyncMock, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from ingestion_module.events.eventbrite import fetch

@pytest.mark.asyncio
async def test_fetch_eventbrite_events_success(monkeypatch):
    # Mocked HTML with embedded window.__SERVER_DATA__ JSON
    fake_events = [
        {
            "name": "AI Conference 2025",
            "start_date": "2025-11-01",
            "timezone": "Africa/Nairobi",
            "url": "https://eventbrite.com/e/ai-conference-2025",
            "id": "evt123",
            "summary": "A conference about AI.",
            "is_online_event": "true",
            "primary_organizer_id": "org456",
            "tags": [{"display_name": "AI"}, {"display_name": "Conference"}]
        }
    ]
    fake_json = {
        "search_data": {
            "events": {
                "results": fake_events
            }
        }
    }
    fake_html = f"""
    <html>
    <head></head>
    <body>
    <script>
    window.__SERVER_DATA__ = {json.dumps(fake_json)};
    </script>
    </body>
    </html>
    """

    # Mock the httpx.AsyncClient.get method
    class MockResponse:
        def __init__(self, text):
            self.text = text
            self.status_code = 200
        def raise_for_status(self): pass

    class MockAsyncClient:
        async def get(self, url):
            return MockResponse(fake_html)

    client = MockAsyncClient()
    url = "https://www.eventbrite.com/d/kenya/ai/"

    result = await fetch.fetch_eventbrite_events(client, url)
    assert result["source"] == "Eventbrite"
    assert result["title"] == ["AI Conference 2025"]
    assert result["event_date"] == ["2025-11-01"]
    assert result["country"] == ["Africa"]
    assert result["city"] == ["Nairobi"]
    assert result["link"] == ["https://eventbrite.com/e/ai-conference-2025"]
    assert result["event_id"] == ["evt123"]
    assert result["event_summary"] == ["A conference about AI."]
    assert result["event_is_online"] == [True]
    assert result["event_organizer_id"] == ["org456"]
    assert result["tags"] == [["AI", "Conference"]]

@pytest.mark.asyncio
async def test_fetch_eventbrite_events_no_json(monkeypatch):
    # HTML without window.__SERVER_DATA__
    fake_html = "<html><body>No JSON here</body></html>"

    class MockResponse:
        def __init__(self, text):
            self.text = text
            self.status_code = 200
        def raise_for_status(self): pass

    class MockAsyncClient:
        async def get(self, url):
            return MockResponse(fake_html)

    client = MockAsyncClient()
    url = "https://www.eventbrite.com/d/kenya/ai/"

    result = await fetch.fetch_eventbrite_events(client, url)
    # Should return empty lists but source is set
    assert result["source"] == "Eventbrite"
    assert all(isinstance(v, list) or isinstance(v, str) for k, v in result.items() if k != "source")