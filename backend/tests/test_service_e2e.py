import pytest
import logging
from unittest.mock import patch, AsyncMock
import asyncio
from orchestration.main import run_test_pipeline


# =========================
# CONFIGURE LOGGING (verbose like original)
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_service_end_to_end_with_mocks():
    """End-to-end pipeline test using mocked modules and in-memory storage (no DB/network)."""

    logger.info("=" * 80)
    logger.info("STARTING END-TO-END SERVICE FIELD TEST (FULLY MOCKED)")
    logger.info("=" * 80)

    # -----------------------------
    # Prepare ingestion record
    # -----------------------------
    normalized_record = {
        "type": "funding",
        "source": "finsmes",
        "link": ["https://www.finsmes.com/2025/09/salt-ai-mock-test-unique.html"],
        "article_date": ["2025-09-22"],
        "company_name": ["salt ai test"],
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
    # Fake module implementations that operate only on queues
    # -----------------------------
    async def fake_normalization_main(db_pool, ingestion_to_normalization_queue,
                                      normalization_to_enrichment_queue,
                                      normalization_to_storage_queue):
        logger.info("[FAKE NORMALIZATION] starting")
        # Drain ingestion queue and push simplified normalized payloads
        while not ingestion_to_normalization_queue.empty():
            source_name, data = await ingestion_to_normalization_queue.get()
            logger.info(f"[FAKE NORMALIZATION] processing source {source_name}")
            normalized = {
                "company_name": data["company_name"],
                "service": data["service"],
                "painpoints": data["painpoints"],
                "source": source_name,
            }
            await normalization_to_enrichment_queue.put(normalized)
            await normalization_to_storage_queue.put(normalized)

        return {
            "normalization_to_enrichment": normalization_to_enrichment_queue,
            "normalization_to_storage": normalization_to_storage_queue,
        }

    async def fake_enrichment_main(normalization_to_enrichment_queue,
                                   enrichment_to_storage_queue):
        logger.info("[FAKE ENRICHMENT] starting")
        # Consume normalized items and produce enriched records
        while not normalization_to_enrichment_queue.empty():
            normalized = await normalization_to_enrichment_queue.get()
            logger.info(f"[FAKE ENRICHMENT] enriching {normalized}")
            enriched = {
                "apollo_id": "test-salt-ai-mock-123",
                "name": normalized["company_name"][0] if isinstance(normalized["company_name"], list) else normalized["company_name"],
                "service": normalized["service"],
                "painpoints": normalized["painpoints"],
                "city": "san francisco",
                "country": "united states",
            }
            await enrichment_to_storage_queue.put(enriched)

        return enrichment_to_storage_queue

    stored_records = []

    async def fake_storage_main(db_pool, normalization_to_storage_queue, enrichment_to_storage_queue):
        logger.info("[FAKE STORAGE] starting")
        # Optionally process normalization->storage (not used here)
        while not normalization_to_storage_queue.empty():
            _ = await normalization_to_storage_queue.get()

        # Consume enrichment->storage and 'persist' to in-memory list
        while not enrichment_to_storage_queue.empty():
            enriched = await enrichment_to_storage_queue.get()
            logger.info(f"[FAKE STORAGE] storing {enriched}")
            stored_records.append(enriched)

        # Return list of apollo_ids to simulate stored org IDs
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
    # Assertions on in-memory stored_records
    # -----------------------------
    logger.info(f"Stored records captured: {stored_records}")
    assert len(stored_records) > 0, "No records were stored by fake_storage"
    first = stored_records[0]
    assert first.get('apollo_id') == 'test-salt-ai-mock-123'
    assert first.get('service') == ['ai/ml'] or first.get('service') == 'ai/ml'
    assert first.get('painpoints') == [['scaling ai services']] or first.get('painpoints') == ['scaling ai services']

    logger.info("✅ End-to-end (mocked) pipeline assertions passed")


import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from orchestration.main import run_test_pipeline

@pytest.mark.asyncio
async def test_run_test_pipeline_with_mocks():
    """
    Run run_test_pipeline end-to-end with mock-only modules.
    No DB or network calls.
    """

    # --- Test input: one normalized record, keyed by source name ---
    normalized_record = {
        "type": "funding",
        "source": "finsmes",
        "link": ["https://www.finsmes.com/2025/09/salt-ai-mock-test-unique.html"],
        "company_name": ["salt ai test"],
        "service": ["ai/ml"],
        "painpoints": [["scaling ai services"]],
    }
    test_ingested_data = {"finsmes": normalized_record}

    # --- Fake modules that simulate behavior using queues ---

    async def fake_normalization_main(db_pool, ingestion_to_normalization_queue,
                                      normalization_to_enrichment_queue,
                                      normalization_to_storage_queue):
        """
        Consume all ingestion items and put lightweight normalized items to both
        the normalization->enrichment queue and normalization->storage queue.
        Return a dict { 'normalization_to_enrichment': queue, 'normalization_to_storage': queue }
        as the real function does.
        """
        # drain ingestion queue
        while not ingestion_to_normalization_queue.empty():
            source_name, data = await ingestion_to_normalization_queue.get()
            # produce a simplified normalized payload
            normalized = {
                "company_name": data["company_name"],
                "service": data["service"],
                "painpoints": data["painpoints"],
                "source": source_name,
            }
            # put same normalized payload to both downstream queues
            await normalization_to_enrichment_queue.put(normalized)
            await normalization_to_storage_queue.put(normalized)

        return {
            "normalization_to_enrichment": normalization_to_enrichment_queue,
            "normalization_to_storage": normalization_to_storage_queue
        }

    async def fake_enrichment_main(normalization_to_enrichment_queue,
                                   enrichment_to_storage_queue):
        """
        Consume normalization->enrichment queue and produce enriched records
        to enrichment->storage queue.
        """
        while not normalization_to_enrichment_queue.empty():
            normalized = await normalization_to_enrichment_queue.get()
            # produce enriched record (adds apollo_id / organization id)
            enriched = {
                "apollo_id": "test-salt-ai-mock-123",
                "name": normalized["company_name"][0] if isinstance(normalized["company_name"], list) else normalized["company_name"],
                "service": normalized["service"],
                "painpoints": normalized["painpoints"],
                "city": "san francisco",
                "country": "united states",
            }
            await enrichment_to_storage_queue.put(enriched)

        # The real enrichment_main returns an enrichment queue (list/queue)
        # Return the queue that storage expects to read from
        return enrichment_to_storage_queue

    async def fake_storage_main(db_pool, normalization_to_storage_queue, enrichment_to_storage_queue):
        """
        Consume normalization->storage and enrichment->storage queues and return
        list of stored organization ids (simulate DB writes without touching DB).
        """
        stored_ids = []
        # consume normalization->storage items (could create initial records)
        while not normalization_to_storage_queue.empty():
            _ = await normalization_to_storage_queue.get()
            # (we don't produce ids here – storage may rely on enrichment output)

        # consume enrichment->storage items and 'store' them by collecting apollo_id
        while not enrichment_to_storage_queue.empty():
            enriched = await enrichment_to_storage_queue.get()
            # simulate storing by collecting id
            stored_ids.append(enriched.get("apollo_id"))

        return stored_ids

    # Use AsyncMock wrappers around the async functions for patching
    fake_norm = AsyncMock(side_effect=fake_normalization_main)
    fake_enrich = AsyncMock(side_effect=fake_enrichment_main)
    fake_storage = AsyncMock(side_effect=fake_storage_main)

    # Patch the names imported in orchestration.main so run_test_pipeline uses fakes
    with patch('orchestration.main.normalization_main', new=fake_norm), \
         patch('orchestration.main.enrichment_main', new=fake_enrich), \
         patch('orchestration.main.storage_main', new=fake_storage):

        # call run_test_pipeline with a dummy db_pool (not used by our fakes)
        dummy_db_pool = AsyncMock()

        org_ids = await run_test_pipeline(dummy_db_pool, test_data={'ingested_data': test_ingested_data})

        # assertions: our fake_storage collects the apollo id the fake enrichment produced
        assert org_ids == ["test-salt-ai-mock-123"]