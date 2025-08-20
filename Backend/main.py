import json
import aiofiles
import asyncio
import logging
import yappi
from typing import List, Dict, Any, Awaitable, Union, Callable
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data

logger = logging.getLogger()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#This function pairs a name with a coroutine (if all goes well) or with an exception otherwise 
async def wrap(name: str, coroutine: Awaitable[Any] )->tuple[str, Union[Any, Exception]]:
    try:
        result = await coroutine 
        logger.info(f"Coroutine {name} done")
        return name, result
    except Exception as e:
        logger.error(f"Coroutine {name} failed with the exception: {str(e)}")
        return name, e

async def run_ingestion_modules():
    #Each coroutine and it's name
    coroutines = [
        ("finsmes", finsmes_main()),
        ("tech_eu", tech_eu_main()),
        ("techcrunch", techcrunch_main()),
        ("hacker_news", hacker_news_main()),
        ("eventbrite", eventbrite_main())
    ]

    #A list of wrap coroutine objects to be run
    tasks = [wrap(name, coroutine) for name, coroutine in coroutines]

    results = {} #Will store info about each coroutines status

    #Process the coroutines as they complete
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
    for name, result in completed_tasks:
        if isinstance(result, Exception):
            logger.error(f"Task '{name}' failed: {result}")
        else:
            logger.info(f"Task '{name}' completed successfully")

        #Add each coroutine's name and result to the results dictionary
        results[name] = result

    logger.info("All ingestion tasks have been completed")

    logger.info(f"\n============FINAL SUMMARY============")
    for name, result in results.items():
        status = "SUCCESS ✅" if not isinstance(result, Exception) else "FAILED ❌"
        logger.info(f"{name}: {status}")

    return results

#===========PROGRAM'S MAIN CODE==============
async def main():
    #==========1. INGESTION ================
    #=========1.1 Run the ingestion modules==========
    """
    Results below will be a dictionary of dictionaries i.e.
    {
        results = {
            "finmes": {
                "type": "funding",
                "source": "finsmes",
                etc.
            }
        }
    }
    """
    results = await run_ingestion_modules()

    #========1.2 Create ingestion to normalization queue===========
    ingestion_to_normalization_queue = asyncio.Queue()

    #========1.3 Enqueue ingestion result values if they're not exceptions=====
    logger.info("Adding ingestion module results to queue 🚂")
    #Add {"finsmes": {}, "tech_eu": {}, "eventbrite": {}}
    for name, result in results.items():
        if not isinstance(result, Exception) and isinstance(result, dict) and result.get("type"):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")
        else:
            logger.error(f"Skipping {name} as its results were empty")

    #==============2. NORMALIZATION================
    #2.1 =========Fetch from queue============
    logger.info("Normalizing ingested data")
    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get()
        logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

    #2.2 ==========Normalize data ===============
        if isinstance(data, dict) and data.get("type") == "event": 
            normalized_event_data = await normalize_event_data(data)
            logger.info(f"Normalized event data from {name}")
            file_name = data.get("source")
            async with aiofiles.open(f"{file_name}.txt", "a") as event_file:
                await event_file.write(json.dumps(normalized_event_data, indent=2))

        elif isinstance(data, dict) and data.get("type") == "funding":
            normalized_funding_data = await normalize_funding_data(data)
            logger.info(f"Normalized funding data from {name}")
            file_name = data.get("source")
            async with aiofiles.open(f"{file_name}.txt", "a") as funding_file:
                await funding_file.write(json.dumps(normalized_funding_data, indent=2))

        elif isinstance(data, dict) and data.get("type") == "hiring":
            normalized_hiring_data = await normalize_hiring_data(data)
            logger.info(f"Normalized hiring data from {name}")
            file_name = data.get("source")
            async with aiofiles.open(f"{file_name}.txt", "a") as hiring_file:
                await hiring_file.write(json.dumps(normalized_hiring_data, indent=2))

    #==============3. ENRICHMENT================
    #2.1 =========Fetch from queue============

if __name__ == "__main__":
    logger.info("Application running....")
    yappi.set_clock_type("WALL")
    yappi.start(builtins=True)
    try:
        asyncio.run(main())
    finally:
        yappi.stop()

    profile_stats = yappi.get_func_stats()
    logger.info("========PROFILED STATS=======")
    profile_stats.print_all()

    profile_stats_filename = "profile_stats"
    profile_stats_file_type = "pstat"
    logger.info(f"Saving profile stats to file {profile_stats_filename}..")
    profile_stats.save(f"{profile_stats_filename}.{profile_stats_file_type}", type=profile_stats_file_type)
    logger.info("Profile saved")

    logger.info("Application Done")