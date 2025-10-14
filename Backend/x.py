import asyncio
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.funding.google_news.fetch import main as google_news_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
import logging
from typing import List, Dict, Any, Awaitable, Union, Callable

logger=logging.getLogger()
logging.basicConfig(level=logging.INFO)

async def wrap(name: str, coroutine: Awaitable[Any] )->tuple[str, Union[Any, Exception]]:
    """Wraps an async coroutine to catch exceptions and return a structured result."""
    try:
        result = await coroutine 
        logger.info(f"Coroutine {name} done")
        return name, result
    except Exception as e:
        logger.error(f"Coroutine {name} failed with the exception: {str(e)}")
        # When a coroutine fails with an exception, return the exception object
        return name, e
        
async def run_ingestion_modules():
    # Each coroutine and its name
    coroutines = [
        ("finsmes", finsmes_main()),
        ("tech_eu", tech_eu_main()),
        ("techcrunch", techcrunch_main()),
        ("hacker_news", hacker_news_main()),
        ("eventbrite", eventbrite_main()),
        ("google_news", google_news_main())
    ]

    # A list of wrap coroutine objects to be run
    tasks = [wrap(name, coroutine) for name, coroutine in coroutines]

    results = {} # Will store info about each coroutine's status

    # Process the coroutines as they complete
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=False) # return_exceptions=False here since wrap handles exceptions
    
    for name, result in completed_tasks:
        if isinstance(result, Exception):
            # Case 1: True execution failure (e.g., network error, raised exception)
            logger.error(f"Task '{name}' failed with exception: {result}")
        elif result and isinstance(result, dict) and result.get('records_found', -1) == 0:
            # Case 2: Successful execution, but zero records found (e.g., TechCrunch/Tech.eu logs)
            logger.warning(f"Task '{name}' completed, but found 0 records: {result.get('message', 'No data')}")
        else:
            # Case 3: Successful execution with data (or if data count wasn't provided, we assume success)
            record_count = result.get('records_found', '?') if isinstance(result, dict) else '?'
            logger.info(f"Task '{name}' completed successfully (Found {record_count} records)")

        # Add each coroutine's name and result to the results dictionary
        results[name] = result

    logger.info("All ingestion tasks have been completed")

    logger.info(f"\n============FINAL SUMMARY============")
    for name, result in results.items():
        status = "SUCCESS ✅" 
        if isinstance(result, Exception):
            status = "FAILED ❌ (Execution Error)"
        elif isinstance(result, dict) and result.get('records_found', -1) == 0:
            status = f"WARNING 🟡 (0 Records Found - {result.get('message', 'No data')})"
        
        logger.info(f"{name}: {status}")

    return results

if __name__ == "__main__":
    asyncio.run(run_ingestion_modules())
