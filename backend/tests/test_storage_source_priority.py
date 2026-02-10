import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from storage_module.company_storage import company_storage

@pytest.mark.asyncio
async def test_company_data_source_priority():
    """
    Test that company_data_source picks the first matching source (funding)
    and is not overwritten by subsequent matches (hiring).
    """
    # Mock pool
    mock_pool = AsyncMock()
    
    # Mock data with both funding and hiring for the same company
    all_normalized_data = [
        {
            "type": "funding",
            "company_name": ["test company"]
        },
        {
            "type": "hiring",
            "company_name": ["test company"]
        }
    ]
    
    searched_orgs = [
        {
            "organizations": [
                {
                    "organization_headcount_six_month_growth": 0.1,
                    "organization_headcount_twelve_month_growth": 0.2
                }
            ]
        }
    ]
    bulk_enriched_orgs = [
        [{
            "organizations": [
                {
                    "id": "123",
                    "name": "Test Company",
                    "website_url": "test.com"
                }
            ]
        }]
    ]
    single_enriched_orgs = [
        {
            "organization": {
                "name": "Test Company"
            }
        }
    ]

    # Mock DB services
    with patch("storage_module.company_storage.is_company_in_db", new_callable=AsyncMock) as mock_is_in_db, \
         patch("storage_module.company_storage.store_to_db", new_callable=AsyncMock) as mock_store, \
         patch("storage_module.company_storage.fetch_source_link", new_callable=AsyncMock) as mock_fetch_link, \
         patch("storage_module.company_storage.fetch_funding_details", new_callable=AsyncMock) as mock_fetch_funding:
        
        mock_is_in_db.return_value = False
        mock_fetch_link.return_value = {"link": "test_link"}
        mock_fetch_funding.return_value = {}

        # Call company_storage
        # We need to pass the arguments that the function expects
        # async def company_storage(pool: asyncpg.Pool, all_normalized_data: List, searched_orgs: List, bulk_enriched_orgs: List, single_enriched_orgs: List):
        results = await company_storage(
            mock_pool, 
            all_normalized_data, 
            searched_orgs, 
            bulk_enriched_orgs, 
            single_enriched_orgs
        )

        # Verify that store_to_db was called with "funding" as the source
        # The company_row is the 22nd element (index 21) in the tuple
        call_args = mock_store.call_args
        data_to_store = call_args.kwargs.get("data_to_store")
        stored_row = data_to_store[0]
        
        assert stored_row[21] == "funding", f"Expected 'funding', got '{stored_row[21]}'"
        print(f"Verified: company_data_source is {stored_row[21]}")

if __name__ == "__main__":
    asyncio.run(test_company_data_source_priority())
