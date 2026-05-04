#Run with ".\.venv\Scripts\python -m pytest tests/test_find_missing_people_endpoint.py -v -s"

import pytest
import asyncpg
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_find_missing_people_endpoint(client):
    """
    Test the /find-missing-people endpoint by mocking all external dependencies.
    This ensures the orchestration flow is correct from request to completion.
    """
    # 1. Setup Mocks
    mock_pool = MagicMock(spec=asyncpg.Pool)
    mock_conn = AsyncMock(spec=asyncpg.Connection)
    
    # Configure mock context managers
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    
    mock_httpx_client = AsyncMock(spec=httpx.AsyncClient)
    
    # 2. Mock individual pipeline steps in utils.find_missing_people
    with patch("main.asyncpg.create_pool", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_pool))), \
         patch("main.httpx.AsyncClient", return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_httpx_client))), \
         patch("utils.find_missing_people.get_uncontacted_companies_without_people", new_callable=AsyncMock) as mock_fetch, \
         patch("utils.find_missing_people.search_for_people", new_callable=AsyncMock) as mock_search, \
         patch("utils.find_missing_people.enrich_people", new_callable=AsyncMock) as mock_enrich, \
         patch("utils.find_missing_people.people_storage", new_callable=AsyncMock) as mock_storage, \
         patch("utils.find_missing_people.outreach_main", new_callable=AsyncMock) as mock_outreach:

        # 3. Define mock behavior
        mock_fetch.return_value = [
            {"org_id": "6759c21b09c8d401b1040a37", "org_domain": "cbam-estimator.com"}
        ]
        
        mock_search_results = {
            "total_entries": 1,
            "people": [{"id": "person_123", "first_name": "Jason"}]
        }
        mock_search.return_value = mock_search_results
        
        mock_enrich_results = [
            {"id": "person_123", "email": "jason@test.com"}
        ]
        mock_enrich.return_value = mock_enrich_results

        # 4. Execute the request
        # Flask handles the async route internally.
        response = client.get('/find-missing-people')

        # 5. Assertions
        assert response.status_code == 200
        assert response.get_json() == {"Success": "Discover people pipeline complete"}

        # 6. Verify pipeline calls
        mock_fetch.assert_called_once_with(mock_pool)
        mock_search.assert_called_once()
        mock_enrich.assert_called_once_with(mock_search_results, mock_httpx_client)
        mock_storage.assert_called_once_with(mock_search_results, mock_enrich_results)
        
        # Outreach should NOT be called now (decoupled)
        mock_outreach.assert_not_called()

        print("\n[OK] End-to-end test for /find-missing-people passed!")
