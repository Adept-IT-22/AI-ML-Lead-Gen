#Run with ".\\.venv\\Scripts\\python -m pytest tests/test_find_missing_people_endpoint.py -v -s"

import pytest
import asyncpg
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

@pytest.mark.asyncio
async def test_find_missing_people_endpoint(client):
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

        # 4. Execute the request — Quart test client is async
        async with client as c:
            response = await c.get('/find-missing-people')

        # 5. Assertions
        assert response.status_code == 200
        data = await response.get_json()
        assert data == {"Success": "Discover people pipeline complete"}

        print("\n[OK] End-to-end test for /find-missing-people passed!")
