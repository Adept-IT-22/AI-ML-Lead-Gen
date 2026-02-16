import pytest
import logging
from unittest.mock import patch, AsyncMock
import asyncio
from orchestration.main import run_test_pipeline

# =========================
# CONFIGURE LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# TEST
# =========================
@pytest.mark.asyncio
async def test_service_end_to_end(db_pool):
    """Full end-to-end test of service field with fully mocked enrichment"""

    logger.info("="*80)
    logger.info("STARTING END-TO-END SERVICE FIELD TEST (FULLY MOCKED)")
    logger.info("="*80)

    # Cleanup any pre-existing test data
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM mock_companies WHERE apollo_id = $1", "test-salt-ai-mock-123")
        await conn.execute("DELETE FROM mock_normalized_master WHERE link LIKE '%salt-ai-mock-test%'")
        logger.info("Cleaned up any existing test data")

    # -----------------------------
    # Prepare ingestion record
    # -----------------------------
    normalized_record = {
        "type": "funding",
        "source": "finsmes",
        "title": [],
        "link": ["https://www.finsmes.com/2025/09/salt-ai-mock-test-unique.html"],
        "article_date": ["2025-09-22"],
        "company_name": ["salt ai test"],
        "city": [],
        "country": [],
        "company_decision_makers": [["test founder"]],
        "company_decision_makers_position": [["ceo"]],
        "funding_round": ["seed"],
        "amount_raised": ["10000000"],
        "currency": ["us dollar"],
        "investor_companies": [["test ventures"]],
        "investor_people": [[]],
        "tags": [[]],
        "painpoints": [["scaling ai services"]],
        "service": ["ai/ml"]
    }

    test_ingested_data = {"finsmes": normalized_record}

    logger.info("STEP 1: INPUT DATA PREPARED")
    logger.info(f"Company Name: {normalized_record['company_name']}")
    logger.info(f"Service Field: {normalized_record['service']}")
    logger.info(f"Painpoints: {normalized_record['painpoints']}")

    # -----------------------------
    # Mock responses
    # -----------------------------
    mock_normalized_batch = [normalized_record]  # list of dicts for enrichment

    mock_org_search_response = [
        {
            "organizations": [
                {
                    "id": "test-salt-ai-mock-123",
                    "name": "salt ai test",
                    "website_url": "http://saltaitest.com",
                    "primary_domain": "saltaitest.com"
                }
            ]
        }
    ]

    mock_bulk_enrichment_response = [[
        {
            "status": "success",
            "organizations": [
                {
                    "id": "test-salt-ai-mock-123",
                    "name": "salt ai test",
                    "service": "ai/ml",
                    "painpoints": ["scaling ai services"],
                    "city": "san francisco",
                    "country": "united states",
                    "apollo_id": "test-salt-ai-mock-123"
                }
            ]
        }
    ]]
    
    mock_single_enrichment_response = [
        {
            "organization": {
                "id": "test-salt-ai-mock-123",
                "name": "salt ai test",
                "apollo_id": "test-salt-ai-mock-123"
            }
        }
    ]

    # -----------------------------
    # Patch all enrichment & network calls
    # -----------------------------
    with patch('orchestration.enrichment.organization_search', new_callable=AsyncMock) as mock_org_search, \
         patch('orchestration.enrichment.bulk_organization_enrichment', new_callable=AsyncMock) as mock_bulk, \
         patch('orchestration.enrichment.single_organization_enrichment', new_callable=AsyncMock) as mock_single, \
         patch('orchestration.enrichment.people_search', new_callable=AsyncMock) as mock_people, \
         patch('orchestration.enrichment.people_enrichment', new_callable=AsyncMock) as mock_people_enrich, \
         patch('services.db_service.is_company_in_db', new_callable=AsyncMock) as mock_in_db, \
         patch('httpx.AsyncClient', new_callable=AsyncMock) as mock_httpx:

        # Configure mocks
        mock_in_db.return_value = False
        mock_org_search.return_value = mock_org_search_response
        mock_bulk.return_value = mock_bulk_enrichment_response
        mock_single.return_value = mock_single_enrichment_response
        mock_people.return_value = {"total_entries": 0, "people": []}
        mock_people_enrich.return_value = {}

        # Mock httpx client to prevent real network
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        mock_httpx.return_value.__aexit__.return_value = AsyncMock()

        logger.info("✅ All mocks configured - NO real API calls will be made")

        # -----------------------------
        # Run the test pipeline
        # -----------------------------
        logger.info("STEP 3: RUNNING PIPELINE")
        org_ids = await run_test_pipeline(db_pool, test_data={'ingested_data': test_ingested_data})
        logger.info(f"Organization IDs returned: {org_ids}")

    # -----------------------------
    # Verify results in DB
    # -----------------------------
    async with db_pool.acquire() as conn:
        companies = await conn.fetch(
            "SELECT name, service, painpoints, apollo_id, city, country, company_data_source FROM mock_companies WHERE apollo_id = $1",
            "test-salt-ai-mock-123"
        )
        logger.info(f"Found {len(companies)} matching company(ies)")

        assert len(companies) > 0, "Company with apollo_id test-salt-ai-mock-123 not found"
        assert companies[0]["service"] == "ai/ml"
        assert companies[0]["painpoints"] == ["scaling ai services"]
        assert companies[0]["company_data_source"] == "funding"
        assert companies[0]["apollo_id"] == "test-salt-ai-mock-123"

        # Cleanup test data
        await conn.execute("DELETE FROM mock_companies WHERE apollo_id = $1", "test-salt-ai-mock-123")
        await conn.execute("DELETE FROM mock_normalized_master WHERE link LIKE '%salt-ai-mock-test%'")
        logger.info("✅ Test data cleaned up")
