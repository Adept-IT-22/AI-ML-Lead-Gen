import asyncio
import logging
from flask import Flask
from flask_cors import CORS
from typing import List, Dict, Any, Awaitable, Union, Callable
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main

logger = logging.getLogger()

app = Flask(__name__)
CORS(app)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    #This function pairs a name with a coroutine (if all goes well) or with an exception otherwise 
    async def wrap(name: str, coroutine: Callable[[], Awaitable[Any]] )->tuple[str, Union[Any, Exception]]:
        try:
            result = await coroutine 
            logger.info(f"Coroutine {name} done")
            return name, result
        except Exception as e:
            logger.error(f"Coroutine {name} failed with the exception: {str(e)}")
            return name, e

    async def main():
        #Each coroutine and it's name
        coroutines = [
            ("finsmes", finsmes_main()),
            ("tech_eu", tech_eu_main()),
            ("techcrunch", techcrunch_main()),
            ("hacker_news", hacker_news_main())
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
            if isinstance(result, Exception):
                logger.error(f"Final status for {name}: FAILED ❌")
            else:
                logger.info(f"Final state for {name}: SUCCESS ✅")

    asyncio.run(main())
