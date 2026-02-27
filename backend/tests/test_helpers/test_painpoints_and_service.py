import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from helpers.painpoints_and_service import get_painpoints_and_service, ai_generated_painpoints_and_service

@pytest.mark.asyncio
async def test_ai_generated_painpoints_and_service_success():
    # Mock the Gemini API call
    mock_response = MagicMock()
    mock_response.candidates = [
        MagicMock(content=MagicMock(parts=[MagicMock(text='{"painpoints": ["p1", "p2"], "service": "ai/ml"}')]))
    ]
    
    with patch('helpers.painpoints_and_service.call_gemini_api', new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_response
        
        result = await ai_generated_painpoints_and_service("Some company description")
        
        assert result == {"painpoints": ["p1", "p2"], "service": "ai/ml"}
        mock_api.assert_called_once()

@pytest.mark.asyncio
async def test_ai_generated_painpoints_and_service_invalid_json():
    # Mock the Gemini API call with invalid JSON
    mock_response = MagicMock()
    mock_response.candidates = [
        MagicMock(content=MagicMock(parts=[MagicMock(text='Invalid JSON')]))
    ]
    
    with patch('helpers.painpoints_and_service.call_gemini_api', new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_response
        
        result = await ai_generated_painpoints_and_service("Some company description")
        
        assert "error" in result
        assert result["raw_text"] == "Invalid JSON"

@pytest.mark.asyncio
async def test_get_painpoints_and_service_empty_queue():
    queue = asyncio.Queue()
    result = await get_painpoints_and_service(queue)
    assert result == []

@pytest.mark.asyncio
async def test_get_painpoints_and_service_success():
    queue = asyncio.Queue()
    test_data = {
        "bulk_enriched_orgs": [[{
            "organizations": [{
                "short_description": "Data driven AI sales tools"
            }]
        }]]
    }
    await queue.put(test_data)
    
    with patch('helpers.painpoints_and_service.ai_generated_painpoints_and_service', new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"painpoints": ["p1"], "service": "ai/ml"}
        
        result = await get_painpoints_and_service(queue)
        
        assert result == {"painpoints": ["p1"], "service": "ai/ml"}
        mock_ai.assert_called_with("Data driven AI sales tools")
