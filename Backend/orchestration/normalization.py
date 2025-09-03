import json
import aiofiles
import asyncio
import logging
from orchestration.ingestion import run_ingestion_modules
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data

logger = logging.getLogger()

async def normalize_data(
        ingestion_to_normalization_queue: asyncio.Queue,
        normalization_to_enrichment_queue: asyncio.Queue
        ):

    logger.info("Normalization started....")

    for name, result in results.items():
        if not isinstance(result, Exception) and isinstance(result, dict) and result.get("type"):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")
        else:
            logger.error(f"Skipping {name} as its results were empty")

    #==============2. NORMALIZATION================
    #2.1 =========Fetch from queue============
    logger.info("Normalizing ingested data....")
    all_normalized_data = []

    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get()
        logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

    #2.2 ==========Normalize data ===============
        data_type = data.get("type")
        if isinstance(data, dict) and data_type == "event": 
            normalized_data= await normalize_event_data(data)

        elif isinstance(data, dict) and data_type == "funding":
            normalized_data = await normalize_funding_data(data)

        elif isinstance(data, dict) and data_type == "hiring":
            normalized_data = await normalize_hiring_data(data)

        all_normalized_data.append(normalized_data)
        logger.info(f"Normalized {data_type} data from {name}")

    async with aiofiles.open("normalized.txt", "a") as file:
        await file.write(json.dumps(all_normalized_data, indent=2))

    logger.info("Done normalizing ingested data")

    #2.3 ==========Put In Normalization-Enrichment Queue===========
    logger.info("Adding normalized data to queue...")
    await normalization_to_enrichment_queue.put(all_normalized_data)
    logger.info(f"Done adding {len(all_normalized_data)} normalized items to queue")