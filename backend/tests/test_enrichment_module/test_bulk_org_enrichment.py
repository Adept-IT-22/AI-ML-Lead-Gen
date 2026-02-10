import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../enrichment_module")))
from enrichment_module import bulk_org_enrichment

@pytest.mark.asyncio
async def test_bulk_org_enrichment_success(monkeypatch):
    # Mock response for client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"domain": "apollo.io"}, {"domain": "microsoft.com"}]}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    company_websites = ["http://www.apollo.io", "www.microsoft.com"]
    result = await bulk_org_enrichment.bulk_org_enrichment(mock_client, company_websites)
    assert "results" in result
    assert result["results"][0]["domain"] == "apollo.io"
    assert result["results"][1]["domain"] == "microsoft.com"

@pytest.mark.asyncio
async def test_bulk_org_enrichment_empty_list(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await bulk_org_enrichment.bulk_org_enrichment(mock_client, [])
    assert "results" in result

@pytest.mark.asyncio
async def test_bulk_org_enrichment_api_error(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    company_websites = ["http://www.apollo.io"]
    result = await bulk_org_enrichment.bulk_org_enrichment(mock_client, company_websites)
    assert "Error" in result
    assert "API error" in result["Error"]