import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../enrichment_module")))
from enrichment_module import people_search

@pytest.mark.asyncio
async def test_people_search_success(monkeypatch):
    # Mock response for client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"people": [{"name": "Alice"}, {"name": "Bob"}]}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    org_ids = ["org1", "org2"]
    org_domains = ["example.com", "test.com"]

    result = await people_search.people_search(
        mock_client,
        org_ids=org_ids,
        org_domains=org_domains
    )
    assert "people" in result
    assert result["people"][0]["name"] == "Alice"
    assert result["people"][1]["name"] == "Bob"

@pytest.mark.asyncio
async def test_people_search_api_error(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    org_ids = ["org1"]
    org_domains = ["example.com"]

    result = await people_search.people_search(
        mock_client,
        org_ids=org_ids,
        org_domains=org_domains
    )
    assert "Error" in result
    assert "API error" in result["Error"]