import json
import aiofiles
import asyncio
import logging
from orchestration.ingestion import run_ingestion_modules
from services.db_service import *
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data

logger = logging.getLogger()

async def main(
        ingestion_to_normalization_queue: asyncio.Queue, 
        normalization_to_enrichment_queue: asyncio.Queue,
        normalization_to_storage_queue: asyncio.Queue
        )->asyncio.Queue: 

    logger.info("Normalizing ingested data....")
    all_normalized_data = []

    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
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
                logger.warning(f"Unknown data type: {data_type}")
                return

            # Step 2: Insert master (one row per dataset)
            for i, normalized_link in enumerate(normalized_data.get("link")):
                normalized_master_data_to_store = [
                    normalized_data.get("type", ""),
                    normalized_data.get("source", ""),
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
                        normalized_data.get("hiring_reasons")[i] if normalized_data.get("hiring_reasons") and i < len(normalized_data.get("hiring_reasons", [])) else []
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

if __name__ == "__main__":
    async def demo():
        #Populate ingestion_to_normalization_queue
        ingestion_to_normalization_queue = asyncio.Queue()
        normalization_to_enrichment_queue = asyncio.Queue()

        mock_fetched_data = [
            ('finsmes', {
                "type": "funding",
                "source": ["FinSMEs"],
                "title": [],
                "link": ["https://www.finsmes.com/2025/10/socratix-ai-raises-4-1m-in-seed-funding.html"],
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
                "tags": [["AI", "fintech", "fraud", "risk", "startup", "seed funding"]]
            }),
            ('techcrunch', {
                "type": "funding",
                "source": ["TechCrunch"],
                "title": [],
                "link": ["https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/"],
                "article_date": ["2025-10-28"],
                "company_name": ["Mem0"],
                "city": [],
                "country": [],
                "company_decision_makers": [["Taranjeet Singh", "Deshraj Yadav"]],
                "company_decision_makers_position": [["Founder", "Co-founder and CTO"]],
                "funding_round": ["Series A"],
                "amount_raised": ["$24M"],
                "currency": ["USD"],
                "investor_companies": [["Basis Set Ventures", "Kindred Ventures", "Y Combinator", "Peak XV Partners", "GitHub Fund"]],
                "investor_people": [["Dharmesh Shah", "Scott Belsky", "Olivier Pomel", "Thomas Dohmke", "Paul Copplestone", "James Hawkins", "Lukas Biewald", "Brian Balfour", "Philip Rathle", "Jennifer Taylor", "Lan Xuezhao"]],
                "tags": [["AI", "LLM", "memory", "open source", "API", "developers", "startup", "funding", "infrastructure", "Seed Funding"]]
            }),
        ]

        for data in mock_fetched_data:
            await ingestion_to_normalization_queue.put(data)
            print("Data added")

        x = await main(ingestion_to_normalization_queue, normalization_to_enrichment_queue)
        print(x.qsize())

    asyncio.run(demo())