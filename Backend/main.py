import asyncio
import logging
from flask import Flask
from flask_cors import CORS
from typing import List, Dict, Any, Awaitable, Union
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main

logger = logging.getLogger()

app = Flask(__name__)
CORS(app)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    async def wrap(name: str, coroutine: callable[str, Awaitable[Any]] )->tuple[str, Union[Any, Exception]]:
        try:
            result = await coroutine
            return name, coroutine
        except Exception as e:
            return name, e

    async def main():
        coroutines = [
            ("finsmes", finsmes_main),
            ("tech_eu", tech_eu_main),
            ("techcrunch", techcrunch_main),
            ("hacker_news", hacker_news_main)
        ]

        tasks = [wrap(name, coroutine) for name, coroutine in coroutines]
        for task_coroutine in asyncio.as_completed(tasks, timeout=10.0):
            name, result = await task_coroutine

            if isinstance(result, Exception):
                logger.error(f"Task '{task.get_name()}' failed: {result}")

    asyncio.run(main())
