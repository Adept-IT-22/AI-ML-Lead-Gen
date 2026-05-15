import json
import aiofiles
import asyncio
import logging
from services.db_service import (
    is_data_in_db,
    store_in_normalized_master,
    store_in_normalized_events,
    store_in_normalized_funding,
    store_in_normalized_hiring,
    DB_URL
)
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data

import asyncpg
from typing import Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def main(
        pool: asyncpg.Pool,
        ingestion_to_normalization_queue: asyncio.Queue, 
        normalization_to_enrichment_queue: asyncio.Queue,
        normalization_to_storage_queue: asyncio.Queue
        )->Dict[str, asyncio.Queue]: 

    logger.info("Normalizing ingested data....")
    all_normalized_data = []

    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get()
        logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

        # ========== Normalize data ===============
        data_type = data.get("type")

        # Step 1: Normalize
        if data_type == "event":
            normalized_data = await normalize_event_data(data)
        elif data_type == "funding":
            normalized_data = await normalize_funding_data(data)
        elif data_type == "hiring":
            normalized_data = await normalize_hiring_data(data)
        else:
            logger.warning(f"Unknown data type: {data_type}. Skipping.")
            continue

        # Step 2: Insert master (one row per dataset)
        for i, normalized_link in enumerate(normalized_data.get("link")):
            normalized_master_data_to_store = [
                normalized_data.get("type", ""),
                normalized_data.get("source")[0] if normalized_data.get("source") else "",
                normalized_link,
                normalized_data.get("title")[i] if normalized_data.get("title") and i < len(normalized_data.get("title", [])) else None,
                normalized_data.get("city")[i] if normalized_data.get("city") and i < len(normalized_data.get("city", [])) else None,
                normalized_data.get("country")[i] if normalized_data.get("country") and i < len(normalized_data.get("country", [])) else None,
                normalized_data.get("tags")[i] if normalized_data.get("tags") and i < len(normalized_data.get("tags", [])) else []
            ]
            data_is_in_db = await is_data_in_db(pool, normalized_link)
            if data_is_in_db:
                continue
            master_id = await store_in_normalized_master(normalized_master_data_to_store, pool)

            # Step 3: Insert children
            if data_type == "event":
                event_data_to_store = [
                    master_id,
                    normalized_data.get("event_id")[i] if normalized_data.get("event_id") and i < len(normalized_data.get("event_id", [])) else None,
                    normalized_data.get("event_summary")[i] if normalized_data.get("event_summary") and i < len(normalized_data.get("event_summary", [])) else None,
                    normalized_data.get("event_is_online")[i] if normalized_data.get("event_is_online") and i < len(normalized_data.get("event_is_online", [])) else None,
                    normalized_data.get("event_organizer_id")[i] if normalized_data.get("event_organizer_id") and i < len(normalized_data.get("event_organizer_id", [])) else None
                ]
                try:
                    await store_in_normalized_events(event_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized events: {str(e)}")

            elif data_type == "funding":
                funding_data_to_store = [
                    master_id,
                    normalized_data.get("company_name")[i] if normalized_data.get("company_name") and i < len(normalized_data.get("company_name", [])) else None,
                    normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers") and i < len(normalized_data.get("company_decision_makers", [])) else [],
                    normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position") and i < len(normalized_data.get("company_decision_makers_position", [])) else [],
                    normalized_data.get("funding_round")[i] if normalized_data.get("funding_round") and i < len(normalized_data.get("funding_round", [])) else None,
                    normalized_data.get("amount_raised")[i] if normalized_data.get("amount_raised") and i < len(normalized_data.get("amount_raised", [])) else None,
                    normalized_data.get("currency")[i] if normalized_data.get("currency") and i < len(normalized_data.get("currency", [])) else None,
                    normalized_data.get("investor_companies")[i] if normalized_data.get("investor_companies") and i < len(normalized_data.get("investor_companies", [])) else [],
                    normalized_data.get("investor_people")[i] if normalized_data.get("investor_people") and i < len(normalized_data.get("investor_people", [])) else [],
                    normalized_data.get("painpoints")[i] if normalized_data.get("painpoints") and i < len(normalized_data.get("painpoints", [])) else [],
                ]

                try:
                    await store_in_normalized_funding(funding_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized funding: {str(e)}")

            elif data_type == "hiring":
                hiring_data_to_store = [
                    master_id,
                    normalized_data.get("company_name")[i] if normalized_data.get("company_name") and i < len(normalized_data.get("company_name", [])) else None,
                    normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers") and i < len(normalized_data.get("company_decision_makers", [])) else [],
                    normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position") and i < len(normalized_data.get("company_decision_makers_position", [])) else [],
                    normalized_data.get("job_roles")[i] if normalized_data.get("job_roles") and i < len(normalized_data.get("job_roles", [])) else [],
                    normalized_data.get("hiring_reasons")[i] if normalized_data.get("hiring_reasons") and i < len(normalized_data.get("hiring_reasons", [])) else [],
                    normalized_data.get("painpoints")[i] if normalized_data.get("painpoints") and i < len(normalized_data.get("painpoints", [])) else []
                ]
                try:
                    await store_in_normalized_hiring(hiring_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized hiring data: {str(e)}")

        all_normalized_data.append(normalized_data)
        logger.info(f"Normalized {data_type} data from {name}")

    async with aiofiles.open("normalized.txt", "a") as file:
        await file.write(json.dumps(all_normalized_data, indent=2))

    logger.info("Done normalizing ingested data")

    #2.3 ==========Put In Normalization-Enrichment Queue===========
    logger.info("Adding normalized data to queues...")

    await normalization_to_enrichment_queue.put(all_normalized_data)
    await normalization_to_storage_queue.put(all_normalized_data)

    logger.info(f"Done adding {len(all_normalized_data)} normalized items to queues")

    return {
        "normalization_to_enrichment": normalization_to_enrichment_queue,
        "normalization_to_storage": normalization_to_storage_queue
    }

# Alias used by tests (2-queue signature. no storage queue needed)
async def x(
        ingestion_to_normalization_queue: asyncio.Queue,
        normalization_to_enrichment_queue: asyncio.Queue,
) -> None:
    normalization_to_storage_queue = asyncio.Queue()
    await main(None, ingestion_to_normalization_queue, normalization_to_enrichment_queue, normalization_to_storage_queue)

if __name__ == "__main__":
    async def demo():
        #Populate ingestion_to_normalization_queue
        ingestion_to_normalization_queue = asyncio.Queue()
        normalization_to_enrichment_queue = asyncio.Queue()
        normalization_to_storage_queue = asyncio.Queue()

        mock_fetched_data = [
            ('finsmes', {
                "type": "funding",
                "source": ["FinSMEs"],
                "title": [],
                "link": ["https://www.finsmes.com/2025/10/socratix-ai-raises-4-1m-in-seed-funding.htmll"],
                "article_date": ["2025-10-29"],
                "company_name": ["Socratix AI"],
                "city": [],
                "country": [],
                "company_decision_makers": [["Riya Jagetia", "Satya Vasanth Tumati"]],
                "company_decision_makers_position": [["Co-founder", "Co-founder"]],
                "funding_round": ["Seed"],
                "amount_raised": ["$4.1M"],
                "currency": ["USD"],
                "investor_companies": [["Pear VC", "Y Combinator", "Twenty Two Ventures", "Transpose Platform Management"]],
                "investor_people": [[]],
                "tags": [["AI", "fintech", "fraud", "risk", "startup", "seed funding"]],
                'painpoints': [["growing constraints of today's AI systems", 'expensive and difficult to sustain as systems move beyond static training', 'need for new computing paradigms that prioritize efficiency, stability, and reliability'], ['traditional SEO strategies are no longer sufficient']]
            })
        ]

        for data in mock_fetched_data:
            await ingestion_to_normalization_queue.put(data)
            print("Data added")

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            x = await main(pool, ingestion_to_normalization_queue, normalization_to_enrichment_queue, normalization_to_storage_queue)
            print(x['normalization_to_storage'].qsize())
            print(await x['normalization_to_storage'].get())

    asyncio.run(demo())