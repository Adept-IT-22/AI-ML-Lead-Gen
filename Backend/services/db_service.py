import os
import logging
import asyncio
import asyncpg
from typing import List, Any, Tuple
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)
DB_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def initialize_db():
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        if conn:
            logger.info("Connection Made")
    except Exception as e:
        logger.error("Sikujui!")

async def fetch_companies():
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        query = "SELECT * FROM companies"
        results = await conn.fetch(query)
        for result in results:
            logger.info(f"This is the result: {result}")
    except Exception as e:
        logger.error(f"Didn't work boy! {str(e)}")

#Store company data to database
async def store_to_db(
        data_to_store: List[Tuple[Any]],
        query: str,
        company_or_people: str
    )->bool: #True = it worked. False = it failed
    
    logger.info(f"Storing {company_or_people} data...")
    
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.executemany(query, data_to_store)               
        await conn.close()

        logger.info("Completed storing company data")
        return True

    except Exception as e:
        logger.error(f"Failed to store company data. {str(e)}")
        return False

if __name__ == "__main__":
    async def main():
        await fetch_companies()

    asyncio.run(main())