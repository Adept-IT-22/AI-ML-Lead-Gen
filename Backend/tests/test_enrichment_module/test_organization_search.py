import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../enrichment_module")))
from enrichment_module import organization_search

@pytest.mark.asyncio
async def test_org_search_success(monkeypatch):
    # Mock response for client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"organizations": [{"name": "CoLoop"}]}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await organization_search.org_search(mock_client, "CoLoop")
    assert "organizations" in result
    assert result["organizations"][0]["name"] == "CoLoop"

@pytest.mark.asyncio
async def test_org_search_api_error(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await organization_search.org_search(mock_client, "CoLoop")
    assert "Error" in result
    assert "API error" in result["Error"]