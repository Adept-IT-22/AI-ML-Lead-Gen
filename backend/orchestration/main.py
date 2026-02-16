import os
import asyncpg
import asyncio
import logging
from dotenv import load_dotenv
from orchestration.ingestion import main as ingestion_main
from orchestration.normalization import main as normalization_main
from orchestration.enrichment import main as enrichment_main
from orchestration.storage import main as storage_main
from orchestration.scoring import main as scoring_main
from orchestration.outreach import main as outreach_main

load_dotenv(override=True)
DB_URL = os.getenv("MOCK_DATABASE_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():

    # ===========QUEUE CREATION ===============
    ingestion_to_normalization_queue = asyncio.Queue()
    normalization_to_enrichment_queue= asyncio.Queue()
    normalization_to_storage_queue= asyncio.Queue()
    enrichment_to_storage_queue = asyncio.Queue()

    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=100) as pool:

        ingestion_module_queue = await ingestion_main(
            ingestion_to_normalization_queue
        )

        normalization_module_queues_dict = await normalization_main(
            pool,
            ingestion_to_normalization_queue=ingestion_module_queue,
            normalization_to_enrichment_queue=normalization_to_enrichment_queue,
            normalization_to_storage_queue=normalization_to_storage_queue
        )

        normalization_to_enrichment = normalization_module_queues_dict.get("normalization_to_enrichment", {})
        normalization_to_storage = normalization_module_queues_dict.get("normalization_to_storage", {})

        enrichment_module_queue = await enrichment_main(
            normalization_to_enrichment_queue=normalization_to_enrichment,
            enrichment_to_storage_queue=enrichment_to_storage_queue
        )

        org_ids = await storage_main(
            pool,
            normalization_to_storage_queue=normalization_to_storage,
            enrichment_to_storage_queue=enrichment_module_queue
        )

        await scoring_main(
            pool
        )

        await outreach_main(
            pool,
            organization_ids=org_ids
        )
        

# FOR TESTING PURPOSES ONLY
async def run_test_pipeline(db_pool, test_data):
    """
    Test version of the pipeline that accepts mocked ingestion data.
    Accepts:
      - db_pool: asyncpg pool
      - test_data: dict containing 'ingested_data' as {source_name: normalized_data_dict}
    Returns:
      - List of organization IDs that were stored
    """

    logger.info("🔹 Running test pipeline: Ingestion → Normalization → Enrichment → Storage")

    # Queues between modules
    ingestion_to_normalization_queue = asyncio.Queue()
    normalization_to_enrichment_queue = asyncio.Queue()
    normalization_to_storage_queue = asyncio.Queue()
    enrichment_to_storage_queue = asyncio.Queue()

    # -----------------------------
    # Step 1: Mock ingestion
    # -----------------------------
    logger.info("Step 1: Mock ingestion")
    ingested_data = test_data.get("ingested_data", {})
    for source_name, data in ingested_data.items():
        # Put data in format expected by normalization: (source_name, data)
        await ingestion_to_normalization_queue.put((source_name, data))
    logger.info(f"  Pushed {len(ingested_data)} source(s) to normalization queue")

    # -----------------------------
    # Step 2: Run REAL normalization
    # -----------------------------
    logger.info("Step 2: Running normalization")
    normalization_module_queues_dict = await normalization_main(
        db_pool,
        ingestion_to_normalization_queue=ingestion_to_normalization_queue,
        normalization_to_enrichment_queue=normalization_to_enrichment_queue,
        normalization_to_storage_queue=normalization_to_storage_queue
    )
    
    normalization_to_enrichment = normalization_module_queues_dict.get("normalization_to_enrichment", {})
    normalization_to_storage = normalization_module_queues_dict.get("normalization_to_storage", {})
    
    logger.info("  Normalization complete")

    # -----------------------------
    # Step 3: Run REAL enrichment
    # -----------------------------
    logger.info("Step 3: Running enrichment")
    enrichment_module_queue = await enrichment_main(
        normalization_to_enrichment_queue=normalization_to_enrichment,
        enrichment_to_storage_queue=enrichment_to_storage_queue
    )
    logger.info("  Enrichment complete")

    # -----------------------------
    # Step 4: Run REAL storage
    # -----------------------------
    logger.info("Step 4: Running storage")
    org_ids = await storage_main(
        db_pool,
        normalization_to_storage_queue=normalization_to_storage,
        enrichment_to_storage_queue=enrichment_module_queue
    )
    logger.info(f"✅ Stored {len(org_ids)} organization(s)")
    
    return org_ids