import os
import json
import logging
import asyncio
import asyncpg
from typing import List, Any, Tuple, Dict
from dotenv import load_dotenv
from utils.db_queries import *

load_dotenv(verbose=True, override=True)

#When running the backend locally I use the 2nd DB_URL. When using docker, I use the 1st.
#=======================================================================================

#DB_URL = os.getenv("DATABASE_URL")
DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

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

#Fetch company by ID
async def fetch_company_details(id: int)->List[Dict[str, any]]:
    logger.info(f"Fetching company with ID: {id}")
    try:
        all_companies = await fetch_companies()
        for company in all_companies:
            if company.get("id") == id:
                return company

    except asyncpg.PostgresError as e:
        logger.error(f"Database error occured: {str(e)}")
        return {}

    except Exception as e:
        logger.error(f"Failed to fetch company details for company ID {id}")
        return {}

#Fetch company by apollo id
async def fetch_company_by_apollo_id(apollo_id: str)->Dict:
    logger.info(f"Fetching company with apollo ID {apollo_id}")
    query = "SELECT * FROM companies WHERE apollo_id = $1 LIMIT 1"

    try:
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, apollo_id)
                if results:
                    logger.info("Company found")
                    json_serializable_results = dict(results)
                    return json_serializable_results 
                else:
                    logger.error("No company found")
                    return {}
    except Exception as e:
        logger.error(f"Failed to find company via ID: {str(e)}")
        return {}

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

#Check if company exists in db based on name
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

#Check if company exists in db based on ID
async def is_company_id_in_db(company_apollo_id: str)->bool:
    logger.info(f"Checking if {company_apollo_id} is in DB")
    query = f"SELECT 1 FROM companies WHERE apollo_id = $1 LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, company_apollo_id)

            if results:
                logger.info(f"{company_apollo_id} found")
                return True
            else: 
                logger.info(f"{company_apollo_id} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {company_apollo_id} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {company_apollo_id} from DB: {str(e)}")

    return False

#Check if person exists in db based on apollo id
async def is_person_in_db(apollo_id: str)->bool:
    logger.info(f"Checking if {apollo_id} is in DB")
    query = f"SELECT 1 FROM people WHERE apollo_id = $1 LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, apollo_id)

            if results:
                logger.info(f"{apollo_id} found")
                return True
            else: 
                logger.info(f"{apollo_id} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {apollo_id} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {apollo_id} from DB: {str(e)}")

    return False

#Store normalized funding data in normalized_funding table
async def store_in_normalized_funding(funding_data_to_store: List[any], pool: asyncpg.pool)->bool:
    logger.info("Storing normalized funding data")
    query = normalized_funding_query

    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, *funding_data_to_store)

        logger.info("Funding data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing funding data: {str(e)}")
        return False

#Store normalized hiring data in normalized_hiring table
async def store_in_normalized_hiring(hiring_data_to_store: List[any], pool: asyncpg.pool)->bool:
    logger.info("Storing normalized hiring data")
    query = normalized_hiring_query

    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, *hiring_data_to_store)

        logger.info("Hiring data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing hiring data: {str(e)}")
        return False

#Store normalized events data in normalized_events table
async def store_in_normalized_events(events_data_to_store: List[any], pool: asyncpg.pool)->bool:
    logger.info("Storing normalized events data")
    query = normalized_events_query

    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, *events_data_to_store)

        logger.info("Events data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing events data: {str(e)}")
        return False

#Store normalized data in normalized_master table and return ID
async def store_in_normalized_master(normalized_master_data_to_store: List[any], pool: asyncpg.pool)->int:
    logger.info("Storing normalized master data")
    query = normalized_master_query

    try:
        async with pool.acquire() as conn:
            normalization_id = await conn.fetchval(query, *normalized_master_data_to_store)

        logger.info("Normalization master data stored")
        return normalization_id

    except Exception as e: 
        logger.error(f"Error storing normalization master data: {str(e)}")
        return 0

#Check if data already exists in normalization table
#THIS IS WRONG. CHECK IF IT EXISTS IN MASTER THEN CHECK NORMALIZATION ID IN THE OTHERS!!
async def is_data_in_db(table_name: str, pool: asyncpg.pool, company_or_event_name: str = None)->bool:

    logger.ifno(f"Checking if {company_or_event_name} exists in table {table_name}")
    query = f"SELECT 1 FROM {table_name} WHERE name = $1 LIMIT 1"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
        
        if results:
            logger.info(f"{company_or_event_name} exists in {table_name}")
            return True
        else: 
            logger.error(f"{company_or_event_name} not found.")
            return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while checking if {company_or_event_name} is in {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error while chekcing if {company_or_event_name} is in {table_name}")
        return True

if __name__ == "__main__":
    async def main():
        logger.info(f"THE DB URL IS: {DB_URL}")
        funding_data_to_store = [
            "NeuroTech AI",                                    # company_name
            ["Alice Johnson", "Bob Smith"],                    # decision_makers
            ["CEO", "CTO"],                                    # decision_makers_position
            "Series A",                                        # funding_round
            5000000,                                           # amount_raised
            "US Dollars",                                      # currency
            ["Sequoia Capital", "Andreessen Horowitz"],        # investor_companies
            ["Jane Doe", "Michael Chan"]                       # investor_people
        ]
        try:
            logger.info("Storing funding data...")
            async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
                await store_in_normalized_funding(funding_data_to_store, pool)
            logger.info("Storing successful")
        except Exception as e:
            logger.error("Failed storing funding data: {str(e)}")

    asyncio.run(main())