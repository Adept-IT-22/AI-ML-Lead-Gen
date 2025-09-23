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
            await conn.execute(query, *funding_data_to_store)

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
            await conn.execute(query, *hiring_data_to_store)

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
            await conn.execute(query, *events_data_to_store)

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
            master_id = await conn.fetchval(query, *normalized_master_data_to_store)

        logger.info("Normalization master data stored")
        return master_id

    except Exception as e: 
        logger.error(f"Error storing normalization master data: {str(e)}")
        return 0

#Check if data already exists in normalization table
async def is_data_in_db(pool: asyncpg.pool, company_or_event_link: str = None)->bool:

    logger.info(f"Checking if {company_or_event_link} exists in normalized_master table")
    query = f"SELECT 1 FROM normalized_master WHERE link = $1 LIMIT 1"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query, company_or_event_link)
        
        if results:
            logger.warning(f"{company_or_event_link} exists in normalized_master")
            return True
        else: 
            logger.info(f"{company_or_event_link} not found.")
            return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while checking if {company_or_event_link} is in normalization_master: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"Error while chekcing if {company_or_event_link} is in normalization_master: {str(e)}")
        return True

#Change person contacted_status from uncontacted to contacted
async def change_person_contacted_status(apollo_id: str, pool):
    logger.info(f"Changing {apollo_id}'s contacted status...")
    query = "UPDATE people SET contacted_status = 'contacted' WHERE apollo_id = $1 RETURNING organization_id"

    try:
        async with pool.acquire() as conn:
            organization_id = await conn.fetch(query, apollo_id)
            org_id_json_list = [dict(org_id) for org_id in organization_id]
            org_id = org_id_json_list[0].get("organization_id")

            #Change contacted_status for person's company
            await change_company_contacted_status(apollo_id=str(org_id), pool=pool)

            logger.info(f"Contacted_status update done for person {apollo_id}")
            return 
    except Exception as e:
        logger.info(f"Failed to update contacted_status: {str(e)}")
        return 

#Change company contacted_status from uncontacted to contacted
async def change_company_contacted_status(apollo_id: str, pool):
    logger.info(f"Changing company {apollo_id}'s contacted status...")
    query = "UPDATE companies SET contacted_status = 'contacted' WHERE apollo_id = $1"

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, apollo_id)
            logger.info(f"Contacted_status update done for company {apollo_id}")
            return 
    except Exception as e:
        logger.info(f"Failed to update contacted_status: {str(e)}")
        return 

async def check_master_normalization(pool: asyncpg.pool):
    async with pool.acquire() as conn:
        query = "SELECT * FROM normalized_master"
        results = await conn.execute(query)
    print(results)
    return results

#Get company from normalization_hiring table and return hiring area
async def get_hiring_area(company_name: str, pool)->str:
    logger.info(f"Get hiring area for {company_name}")

    try:
        query = "SELECT * FROM normalized_hiring WHERE LOWER(company_name) = $1 LIMIT 1"
        async with pool.acquire() as conn:
            results = await conn.fetch(query, company_name.lower())
            company_json_list = [dict(result) for result in results]
            company_json = company_json_list[0] 

            job_roles = company_json.get("job_roles")
            hiring_area = job_roles[0] if job_roles else "various areas"
            logger.info(hiring_area)

            return hiring_area

    except Exception as e:
        logger.error(f"Couldn't get hiring area for {company_name}: {str(e)}")
        return ""
    
#Get company funding details from normalized_funding
async def fetch_funding_details(pool: asyncpg.Pool, company_name: str)->Dict:
    logger.info(f"Fetching funding details for {company_name}")
    query = "SELECT funding_round, amount_raised, currency FROM normalized_funding WHERE LOWER(company_name) = $1"

    try:
        async with pool.acquire() as conn:
            response = await conn.fetch(query, company_name.lower())
            response_list = [dict(result) for result in response]

            if not response_list:
                logger.warning(f"No funding data found for {company_name}")
                return {}

            response_dict = response_list[0]
            logger.info("Funding data found")
            return response_dict
    except Exception as e:
        logger.error(f"Failed to fetch funding details for {company_name}: {str(e)}")
        return {}

#Get companies with no funding details
async def return_companies_with_no_funding_details(pool: asyncpg.Pool)->List:
    logger.info("Fetching companies with null funding details")
    query = "SELECT name FROM companies WHERE latest_funding_round IS NULL AND latest_funding_amount IS NULL AND latest_funding_currency IS NULL"
    companies = []

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            for each_dict in results_list:
                name = each_dict.get("name", "")
                companies.append(name)
        logger.info("Done fetching companies")
        return companies
    except Exception as e:
        logger.info(f"Failed fetching companies: {str(e)}") 

#Get link for funding, hiring, events source
async def fetch_source_link(pool: asyncpg.Pool, company_name: str)->Dict:
    logger.info(f"Fetching link for {company_name}...")
    query = fetch_link_query

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query, company_name.lower())
            result_list = [dict(result) for result in results]
            if not result_list:
                logger.warning(f"No source link found for {company_name}")
                return {}

            final_result = result_list[0]
            logger.info("Done fetching link")
            return final_result
    except Exception as e:
        logger.error(f"Failed to fetch link for {company_name}: {str(e)}")
        return {}

#Fetch events from db
async def fetch_events(pool: asyncpg.Pool)->List[Dict[str, str]]:
    logger.info("Fetching events from database")
    query = """
            SELECT m.id, m.source, m.link, e.event_summary
            FROM normalized_master m
            LEFT JOIN normalized_events e ON m.id = e.master_id
            WHERE m.type = 'event';
            """

    try: 
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            if not results_list:
                logger.warning("No events found")
                return []
            
            logger.info("Events found")
            return results_list
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        return []

#Fetch company keywords
async def fetch_keywords(pool):
    query = "SELECT keywords FROM companies"
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            result_list = [dict(result) for result in results]
            logger.info(result_list)
    except Exception as e:
        logger.error(f"Failed to fetch keywords: {str(e)}")

#Select all unscored companies
async def company_is_unscored(pool)->List[Dict[str, int]]:
    logger.info("Fetching all unscored companies...")
    query = "SELECT id FROM companies WHERE icp_score IS NULL"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            return results_list
    except Exception as e:
        logger.error(f"Failed to fetch unscored companies: {str(e)}")
        return []

#Store icp score
async def store_icp_score(pool, company_name, company_id, icp_score):
    logger.info(f"Storing ICP score for {company_name}")
    query = "UPDATE companies SET icp_score = $1 WHERE id = $2"

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, icp_score, company_id)
        logger.info(f"Done storing icp score for {company_name}")
        return
    except Exception as e:
        logger.error(f"Failed to store icp score for {company_name}")
        return

if __name__ == "__main__":
    async def main():
        logger.info(f"THE DB URL IS: {DB_URL}")
        #funding_data_to_store = [
            #"NeuroTech AI",                                    # company_name
            #["Alice Johnson", "Bob Smith"],                    # decision_makers
            #["CEO", "CTO"],                                    # decision_makers_position
            #"Series A",                                        # funding_round
            #5000000,                                           # amount_raised
            #"US Dollars",                                      # currency
            #["Sequoia Capital", "Andreessen Horowitz"],        # investor_companies
            #["Jane Doe", "Michael Chan"]                       # investor_people
        #]

        #async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        await fetch_company_details(52)
    asyncio.run(main())