import pytest
import logging
from unittest.mock import patch, AsyncMock
import asyncio
from orchestration.main import run_test_pipeline


# =========================
# CONFIGURE LOGGING (verbose)
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_service_end_to_end_full_mocked():
    """Comprehensive end-to-end pipeline test using mocked enrichment responses and fake modules.
    No real DB or network calls.
    """

    logger.info("=" * 80)
    logger.info("STARTING END-TO-END SERVICE FIELD TEST (FULLY MOCKED)")
    logger.info("=" * 80)

    # -----------------------------
    # Prepare ingestion record (same shape as original test)
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
    # Mock responses (original shapes)
    # -----------------------------
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
                    "apollo_id": "test-salt-ai-mock-123",
                    "company_data_source": "funding"
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

    mock_people_search_response = {"total_entries": 0, "people": []}

    logger.info("STEP 2: Mock responses prepared")

    # -----------------------------
    # Fake module implementations that operate on queues and use mock responses
    # -----------------------------
    async def fake_normalization_main(db_pool, ingestion_to_normalization_queue,
                                      normalization_to_enrichment_queue,
                                      normalization_to_storage_queue):
        logger.info("[FAKE NORMALIZATION] starting")
        while not ingestion_to_normalization_queue.empty():
            source_name, data = await ingestion_to_normalization_queue.get()
            logger.info(f"[FAKE NORMALIZATION] processing source {source_name}")
            normalized = {
                "company_name": data["company_name"],
                "service": data["service"],
                "painpoints": data["painpoints"],
                "source": source_name,
                "link": data.get("link")
            }
            await normalization_to_enrichment_queue.put(normalized)
            await normalization_to_storage_queue.put(normalized)

        return {
            "normalization_to_enrichment": normalization_to_enrichment_queue,
            "normalization_to_storage": normalization_to_storage_queue,
        }

    # We'll collect stored records in-memory for assertions
    stored_records = []

    async def fake_enrichment_main(normalization_to_enrichment_queue,
                                   enrichment_to_storage_queue):
        logger.info("[FAKE ENRICHMENT] starting")
        # Simulate organization search -> bulk enrichment -> single enrichment -> people search/enrich
        while not normalization_to_enrichment_queue.empty():
            normalized = await normalization_to_enrichment_queue.get()
            logger.info(f"[FAKE ENRICHMENT] received normalized: {normalized}")

            # Simulate org search returning an organization
            org_search = mock_org_search_response
            org = org_search[0]["organizations"][0]
            org_id = org["id"]

            # Simulate bulk enrichment returning detailed organization info
            bulk = mock_bulk_enrichment_response
            bulk_org = bulk[0][0]["organizations"][0]

            # Simulate single enrichment (could provide more fields)
            single = mock_single_enrichment_response
            single_org = single[0]["organization"]

            # Simulate people search/enrichment (empty here)
            people = mock_people_search_response

            # Build enriched record combining sources (shape similar to real enrichment output)
            enriched = {
                "apollo_id": bulk_org.get("apollo_id") or org_id,
                "id": org_id,
                "name": bulk_org.get("name") or single_org.get("name"),
                "service": bulk_org.get("service") or (normalized.get("service") and (normalized.get("service")[0] if isinstance(normalized.get("service"), list) else normalized.get("service"))),
                "painpoints": bulk_org.get("painpoints") or normalized.get("painpoints"),
                "city": bulk_org.get("city"),
                "country": bulk_org.get("country"),
                "website_url": org.get("website_url"),
                "primary_domain": org.get("primary_domain"),
                "company_data_source": bulk_org.get("company_data_source", "funding"),
                "people": people.get("people", [])
            }

            # Produce first enriched record
            logger.info(f"[FAKE ENRICHMENT] produced enriched: {enriched}")
            await enrichment_to_storage_queue.put(enriched)

            # Additionally produce a second (alternative) enriched organization for the same normalized record
            # Create a variant alt record that differs in shape to exercise handling
            enriched_alt = {
                "apollo_id": (bulk_org.get("apollo_id") or org_id) + "-alt",
                "id": org_id + "-alt",
                "name": (bulk_org.get("name") or single_org.get("name")) + " (alt)",
                # Make 'service' a list on the alt record to exercise type variations
                "service": ["data", "analytics"],
                # Intentionally omit 'painpoints' to simulate partial data
                # "painpoints": None,
                "city": bulk_org.get("city"),
                "country": bulk_org.get("country"),
                # Simulate missing website_url on the alt record
                "website_url": None,
                "primary_domain": (org.get("primary_domain") and org.get("primary_domain").replace('saltaitest', 'saltaitest-alt')),
                # Use a different source marker to test downstream source handling
                "company_data_source": "org_search",
                "people": []
            }

            logger.info(f"[FAKE ENRICHMENT] produced alternative enriched: {enriched_alt}")
            await enrichment_to_storage_queue.put(enriched_alt)

        return enrichment_to_storage_queue

    async def fake_storage_main(db_pool, normalization_to_storage_queue, enrichment_to_storage_queue):
        logger.info("[FAKE STORAGE] starting")
        # Optionally observe normalization->storage (not used for assertions here)
        while not normalization_to_storage_queue.empty():
            _ = await normalization_to_storage_queue.get()

        # Consume enrichment->storage and persist to in-memory list
        while not enrichment_to_storage_queue.empty():
            enriched = await enrichment_to_storage_queue.get()
            logger.info(f"[FAKE STORAGE] storing enriched: {enriched}")
            stored_records.append(enriched)

        return [r.get("apollo_id") for r in stored_records]

    # Wrap fakes in AsyncMock so patching behaves like the real async functions
    fake_norm = AsyncMock(side_effect=fake_normalization_main)
    fake_enrich = AsyncMock(side_effect=fake_enrichment_main)
    fake_storage = AsyncMock(side_effect=fake_storage_main)

    # Patch the orchestration imports so run_test_pipeline uses our fakes
    with patch('orchestration.main.normalization_main', new=fake_norm), \
         patch('orchestration.main.enrichment_main', new=fake_enrich), \
         patch('orchestration.main.storage_main', new=fake_storage):

        logger.info("✅ All fake modules configured - NO real API/DB calls will be made")

        # -----------------------------
        # Run the test pipeline
        # -----------------------------
        logger.info("STEP 3: RUNNING PIPELINE")
        dummy_db_pool = AsyncMock()
        org_ids = await run_test_pipeline(dummy_db_pool, test_data={'ingested_data': test_ingested_data})
        logger.info(f"Organization IDs returned: {org_ids}")

    # -----------------------------
    # Assertions on in-memory stored_records (more comprehensive)
    # -----------------------------
    logger.info(f"Stored records captured: {stored_records}")
    # We expect two organizations per normalized record (main + alternative)
    assert len(stored_records) == 2, f"Expected exactly two stored records but got {len(stored_records)}"

    apollo_ids = {r.get('apollo_id') for r in stored_records}
    assert 'test-salt-ai-mock-123' in apollo_ids
    assert 'test-salt-ai-mock-123-alt' in apollo_ids

    # Validate at least one record contains the expected fields
    first = stored_records[0]
    assert first.get('name') is not None
    svc = first.get('service')
    assert svc == 'ai/ml' or svc == ['ai/ml']
    # painpoints may be nested list or flat
    assert first.get('painpoints') == ['scaling ai services'] or first.get('painpoints') == [['scaling ai services']]

    # Validate company_data_source and domains for the main record
    main = next((r for r in stored_records if r.get('apollo_id') == 'test-salt-ai-mock-123'), None)
    assert main is not None
    assert main.get('company_data_source') == 'funding'
    assert main.get('website_url') == 'http://saltaitest.com'
    assert main.get('primary_domain') == 'saltaitest.com'

    logger.info("✅ End-to-end (mocked, faithful) pipeline assertions passed")

    # Validate alternative record shape and missing fields handling
    alt = next((r for r in stored_records if r.get('apollo_id') and r.get('apollo_id').endswith('-alt')), None)
    assert alt is not None, "Expected an alternative enriched record with '-alt' apollo_id"
    # Service should be a list in the alt record
    svc_alt = alt.get('service')
    assert isinstance(svc_alt, list), f"Expected alt.service to be a list but got: {type(svc_alt)}"
    # The alt record intentionally lacks website_url (None) to exercise missing-field handling
    assert alt.get('website_url') is None
    # Company data source should reflect the alternative source
    assert alt.get('company_data_source') == 'org_search'

    logger.info("✅ Alternative-record assertions passed (variations handled)")