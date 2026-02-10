import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../enrichment_module")))
from enrichment_module import single_org_enrichment

@pytest.mark.asyncio
async def test_single_org_enrichment_success(monkeypatch):
    # Mock response for client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"domain": "eagle.org", "enriched": True}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await single_org_enrichment.single_org_enrichment(
        mock_client,
        company_website="eagle.org"
    )
    assert "domain" in result
    assert result["domain"] == "eagle.org"
    assert result["enriched"] is True

@pytest.mark.asyncio
async def test_single_org_enrichment_api_error(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await single_org_enrichment.single_org_enrichment(
        mock_client,
        company_website="eagle.org"
    )
    assert "Error" in result
    assert "API error" in result["Error"]

@pytest.mark.asyncio
async def test_single_org_enrichment_empty_domain(monkeypatch):
    # Should still call API, but with empty domain
    mock_response = MagicMock()
    mock_response.json.return_value = {"domain": "", "enriched": False}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await single_org_enrichment.single_org_enrichment(
        mock_client,
        company_website=""
    )
    assert "domain" in result
    assert result["domain"] == ""
    assert result["enriched"] is False