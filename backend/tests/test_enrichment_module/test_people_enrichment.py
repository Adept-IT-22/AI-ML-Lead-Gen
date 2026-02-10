import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../enrichment_module")))
from enrichment_module import people_enrichment

@pytest.mark.asyncio
async def test_people_enrichment_success(monkeypatch):
    # Mock response for client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"person": {"id": "610c3e23d4d76a0001aa35b3", "name": "Charles Hayter"}}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await people_enrichment.people_enrichment(
        mock_client,
        user_id="610c3e23d4d76a0001aa35b3",
        user_name="Charles Hayter"
    )
    assert "person" in result
    assert result["person"]["id"] == "610c3e23d4d76a0001aa35b3"
    assert result["person"]["name"] == "Charles Hayter"

@pytest.mark.asyncio
async def test_people_enrichment_api_error(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    mock_client = MagicMock()
    # Simulate an exception when post is called
    async def raise_exc(*args, **kwargs):
        raise Exception("API error")
    mock_client.post = AsyncMock(side_effect=raise_exc)

    result = await people_enrichment.people_enrichment(
        mock_client,
        user_id="610c3e23d4d76a0001aa35b3",
        user_name="Charles Hayter"
    )
    # Should return None on error
    assert result is None