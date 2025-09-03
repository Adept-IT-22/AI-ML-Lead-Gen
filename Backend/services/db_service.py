import os
import logging
import asyncio
import asyncpg
from typing import List, Any, Tuple, Dict
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

#Fetches all companies from the database
async def fetch_companies()->List[Dict[str, Any]]:
    logger.info("Fetching companies from DB...")
    try:
        conn = await asyncpg.connect(dsn=DB_URL) 
        query = "SELECT * FROM companies"
        results = await conn.fetch(query)
        await conn.close()
        json_serializable_results = [dict(record) for record in results]
        logger.info("Done fetching companies from DB...")
        print(results)
        return json_serializable_results

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []

    except Exception as e:
        logger.error(f"An unexpected error occured: {str(e)}")
        return []

#Fetch people from database
async def fetch_people()->List[Dict[str, Any]]:
    logger.info("Fetching people from DB...")
    try:
        conn = await asyncpg.connect(dsn=DB_URL) 
        query = "SELECT * FROM people"
        results = await conn.fetch(query)
        await conn.close()
        json_serializable_results = [dict(record) for record in results]
        logger.info("Done fetching people from DB...")
        print(results)
        return json_serializable_results

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch people: {str(e)}")
        return []

    except Exception as e:
        logger.error(f"An unexpected error occured: {str(e)}")
        return []

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

        logger.info(f"Completed storing {company_or_people} data")
        return True

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while storing {company_or_people} data: {str(e)}")
        

    except Exception as e:
        logger.error(f"Failed to store {company_or_people} data: {str(e)}")
        return False

async def clear_table(table_name:str):
    conn = await asyncpg.connect(dsn=DB_URL)
    query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY"
    await conn.execute(query)
    await conn.close()
    print("Success")
    return

if __name__ == "__main__":
    async def main():
        await fetch_people()

    asyncio.run(main())