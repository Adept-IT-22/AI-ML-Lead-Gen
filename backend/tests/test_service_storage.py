# test_service_storage.py
import pytest
from storage_module.company_storage import company_storage

@pytest.mark.asyncio
async def test_service_stored_in_database(db_pool):
    normalized_data = [{
        "type": "hiring",
        "company_name": ["TestCorp"],
        "service": ["AI/ML"],
        "painpoints": [["scaling ML infrastructure"]],
        "city": [""],
        "country": [""],
        "company_decision_makers": [[]],
        "tags": [[]],
        "hiring_reasons": [[]],
        "job_roles": [[]],
        "article_date": ["2026-01-01"],
        "source": "test",
        "link": [""],
        "title": [""]
    }]
    
    # Wrap organizations in the expected structure
    searched_orgs = [{
        "organizations": [{
            "name": "TestCorp",
            "id": "test-apollo-id-123",
            "organization_headcount_six_month_growth": 10,
            "organization_headcount_twelve_month_growth": 25,
            "website_url": "http://test.com",
            "linkedin_url": "http://linkedin.com/test",
            "twitter_url": "",
            "facebook_url": "",
            "primary_phone": "",
            "sanitize_phone": "",
            "organization_id": "test-apollo-id-123",
            "languages": [],
            "alexa_ranking": 0,
            "phone": "",
            "headline": "",
            "logo_url": ""
        }]
    }]
    
    # Bulk enriched orgs also need the nested structure
    bulk_enriched_orgs = [[{
        "organizations": [{
            "id": "test-apollo-id-123",
            "name": "TestCorp",
            "website_url": "http://test.com",
            "linkedin_url": "http://linkedin.com/test",
            "phone": "+1234567890",
            "founded_year": 2020,
            "market_cap": 1000000,
            "industries": ["Technology", "AI/ML"],
            "estimated_num_employees": 50,
            "keywords": ["AI", "Machine Learning"],
            "city": "San Francisco",
            "state": "CA",
            "country": "USA",
            "short_description": "AI/ML company"
        }]
    }]]
    
    # Single enriched orgs structure
    single_enriched_orgs = [{
        "organization": {
            "total_funding": 5000000,
            "technology_names": ["Python", "TensorFlow"],
            "annual_revenue": 2000000,
            "funding_events": [{
                "type": "Series A",
                "amount": "$5M",
                "currency": "USD"
            }]
        }
    }]
    
    # Execute storage
    result = await company_storage(db_pool, normalized_data, searched_orgs, bulk_enriched_orgs, single_enriched_orgs)
    
    # Verify service was stored
    async with db_pool.acquire() as conn:
        # First check if any data was inserted
        count = await conn.fetchval("SELECT COUNT(*) FROM mock_companies")
        print(f"\nTotal companies in DB: {count}")
        
        result = await conn.fetchrow(
            "SELECT service, painpoints, apollo_id, name FROM mock_companies WHERE apollo_id = $1",
            "test-apollo-id-123"
        )
        
        assert result is not None, "No company was stored in the database"
        assert result["service"] == "AI/ML", f"Expected service 'AI/ML', got '{result['service']}'"
        assert result["painpoints"] == ["scaling ML infrastructure"], f"Expected painpoints, got '{result['painpoints']}'"
        print(f"✅ Test passed! Company: {result['name']}, Service: {result['service']}")