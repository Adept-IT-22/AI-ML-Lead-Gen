import json
import asyncio
import logging
from typing import List, Dict, Any, Awaitable, Union, Callable
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
from normalization_module.event_normalization import normalize_event_data

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
    logger.info("Adding ingestion module results to queue")
    #Add {"finsmes": {}, "tech_eu": {}, "eventbrite": {}}
    for name, result in results.items():
        if not isinstance(result, Exception):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")

    logger.info("Done adding ingestion module results to queue")

    #==============2. NORMALIZATION================
    #2.1 =========Fetch from queue============
    logger.info("Normalizing ingested data")
    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get(result)

    #2.2 ==========Normalize data ===============
        if isinstance(data, dict) and data.get("type") == "event": 
            normalized_event_data = normalize_event_data(result)
            logger.info(f"Normalized data from {name}:\n{json.dumps(normalize_event_data, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())