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
        logger.error("Connection not made!")

#Fetches all companies from the database
async def fetch_companies()->List[Dict[str, Any]]:
    logger.info("Fetching companies from DB...")
    try:
        all_companies = []
        conn = await asyncpg.connect(dsn=DB_URL) 

        #Fetch companies
        company_query = "SELECT * FROM companies"
        results = await conn.fetch(company_query)

        #Fetch people for each company
        for result in results:
            company_apollo_id = result.get("apollo_id")
            people_results = await fetch_people_from_company(organization_id=company_apollo_id)
            dict_result = dict(result)
            dict_result["people"] = people_results
            all_companies.append(dict_result)

        await conn.close()
        logger.info("Done fetching companies from DB...")
        return all_companies

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []

    except Exception as e:
        logger.error(f"An unexpected error occured: {str(e)}")
        return []

        
async def fetch_people_from_company(organization_id: str)->List[Dict[str, str]]:
    conn = await asyncpg.connect(dsn=DB_URL)
    people_query = "SELECT full_name, title, email FROM people WHERE organization_id = $1"
    people_results = await conn.fetch(people_query, organization_id)
    await conn.close()
    return [dict(record) for record in people_results]


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

#Check if company exists in db
async def is_company_in_db(company_name: str)->bool:
    logger.info(f"Checking if {company_name} is in DB")
    query = f"SELECT 1 FROM companies WHERE LOWER(name) = LOWER($1) LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, company_name)

            if results:
                logger.info(f"{company_name} found")
                return True
            else: 
                logger.info(f"{company_name} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {company_name} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {company_name} from DB: {str(e)}")

    return False

if __name__ == "__main__":
    async def main():
        await fetch_companies()

    asyncio.run(main())