import logging
import asyncio
from typing import Dict
from helpers.helpers import wrap
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.funding.sifted_eu.fetch import main as sifted_eu_main
from ingestion_module.funding.cbinsights.fetch import main as cbinsights_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def run_ingestion_modules()->Dict:
    #Each coroutine and it's name
    coroutines = [
        ("finsmes", finsmes_main()),
        ("tech_eu", tech_eu_main()),
        ("techcrunch", techcrunch_main()),
        ("sifted_eu", sifted_eu_main()),
        ("cbinsights", cbinsights_main()),
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

#Put results in queue.
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

#Populate queue and return it
async def main(ingestion_to_normalization_queue: asyncio.Queue)->asyncio.Queue:
    results = await run_ingestion_modules()

    logger.info("Adding ingestion module results to queue 🚂")

    #Add {"finsmes": {}, "tech_eu": {}, "eventbrite": {}}
    for name, result in results.items():
        if not isinstance(result, Exception) and isinstance(result, dict) and result.get("type"):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")
        else:
            logger.error(f"Skipping {name} as its results were empty")

    return ingestion_to_normalization_queue


if __name__ == "__main__":
    async def ingestion():
        q = asyncio.Queue()
        x = await main(q)
        for _ in range(x.qsize()):
            print(await x.get())

    asyncio.run(ingestion())