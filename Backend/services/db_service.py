import os
import json
import logging
import asyncio
import asyncpg
from typing import List, Any, Tuple, Dict
from dotenv import load_dotenv
from utils.db_queries import *
from utils.set_conversion import convert_sets

load_dotenv(verbose=True, override=True)

#When running the backend locally I use the 2nd DB_URL. When using docker, I use the 1st.
#=======================================================================================

#DB_URL = os.getenv("DATABASE_URL")
#DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"
DB_URL = "postgresql://lead_gen_user:lead_gen_password@lead-gen-db:5432/lead_gen_db"
#DB_URL = os.getenv("MOCK_DATABASE_URL")

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
async def fetch_companies() -> List[Dict[str, Any]]:
    """
    Fetches all companies and their associated people in a single query (Eager Loading)
    and correctly consolidates the denormalized join results into a nested structure.
    """
    logger.info("Fetching companies from DB...")
    conn = None # Initialize conn outside the try block
    try:
        # 1. Connect to the database
        conn = await asyncpg.connect(dsn=DB_URL)

        # 2. Eager Load Query: Single query using LEFT JOIN to get all data
        company_query = """
        SELECT 
            c.*, 
            p.full_name, p.title, p.email, p.linkedin_url,
            i.top_matches, i.interpretation
        FROM 
            companies c 
        LEFT JOIN 
            people p ON c.apollo_id = p.organization_id

        LEFT JOIN
            icp_scores i ON c.id = i.company_id;
        """
        results = await conn.fetch(company_query)
        
        # 3. Close connection immediately after fetching data
        await conn.close()
        
        # 4. CONSOLIDATION LOGIC: Re-structure the flat 99 rows into 62 nested objects
        companies_map: Dict[str, Dict[str, Any]] = {}

        for record in results:
            # Convert asyncpg.Record to dict for easier manipulation
            record_dict = dict(record)
            print(record_dict)
            company_apollo_id = record_dict.get("apollo_id")

            if company_apollo_id is None:
                # Skip records if the primary company ID is somehow missing
                continue

            # --- CONSOLIDATE COMPANY DATA ---
            if company_apollo_id not in companies_map:
                # A. First time seeing this company: Initialize the master object
                company_data = record_dict.copy()
                company_data["people"] = []

                # Also, add the companies alignment to our services.
                company_data["top_matches"] = record_dict.get('top_matches')
                company_data["interpretation"] = record_dict.get('interpretation')
                
                # Clean up the root object by removing the scattered people data
                del company_data["full_name"]
                del company_data["title"]
                del company_data["email"]
                del company_data["linkedin_url"]
                
                companies_map[company_apollo_id] = company_data
            
            # Get the reference to the master company object
            master_company = companies_map[company_apollo_id]

            # --- CONSOLIDATE PEOPLE DATA ---
            # The 'full_name' field is NULL if the LEFT JOIN found no matching person.
            if record_dict["full_name"]:
                person = {
                    "full_name": record_dict["full_name"],
                    "title": record_dict["title"],
                    "email": record_dict["email"],
                    "linkedin_url": record_dict["linkedin_url"]
                }
                if person not in master_company.get('people'):
                    master_company["people"].append(person)

        # Convert the dictionary values (the 62 unique company objects) back to a list
        final_all_companies = list(companies_map.values())
        logger.info(f"Done fetching and consolidating {len(final_all_companies)} companies.")
        return final_all_companies

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []
    finally:
        if conn:
            # Ensure connection is closed even if an error occurs during fetch
            try:
                await conn.close()
            except Exception:
                pass # Ignore close errors
        
async def fetch_people_from_company(organization_id: str)->List[Dict[str, str]]:
    logger.info(f"Fetching people from org id {organization_id}...")
    conn = await asyncpg.connect(dsn=DB_URL)
    #CHANGED
    people_query = "SELECT full_name, title, email, linkedin_url FROM people WHERE organization_id = $1"
    people_results = await conn.fetch(people_query, organization_id)
    logger.info(f"Done fetching people from org id {organization_id}")
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
async def fetch_company_details(id: int) -> Dict[str, any]:
    logger.info(f"Fetching company with ID: {id}")
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        #CHANGED
        query = """
            SELECT c.*, p.full_name, p.title, p.email, p.linkedin_url, i.top_matches, i.interpretation
            FROM companies c 
            LEFT JOIN people p 
            ON c.apollo_id = p.organization_id
            LEFT JOIN icp_scores i
            ON c.id = i.company_id
            WHERE c.id = $1
            """
        results = await conn.fetch(query, id)
        await conn.close()

        if results:
            #Since the results might be multiple as the company might have many people, 
            #we need to create one dictionary and append the people key with all the people
            final_results = {}
            for result in results:
                #Transform record to dict
                result_dict = dict(result)
                #Copy result dict to avoid manipulating the original one
                result_copy = result_dict.copy()
                #If result is not in final_results, create a people key, remove the shown keys
                #then add it to final_results with its key as the apollo_id
                result_id = result.get('apollo_id')
                if result_id not in final_results:
                    result_copy['people'] = []
                    del result_copy['full_name']
                    del result_copy['title']
                    del result_copy['email']
                    del result_copy['linkedin_url']
                    final_results[result_id] = result_copy

                stored_result = final_results.get(result_id)
                if result_copy.get('full_name'):
                    person = {
                        'full_name': result_dict.get('full_name'),
                        'title': result_dict.get('title'),
                        'email': result_dict.get('email'),
                        'linkedin_url': result_dict.get('linkedin_url'),
                    }
                    if person not in stored_result.get('people'):
                        stored_result.get('people').append(person)

                stored_result['top_matches'] = result_copy.get('top_matches')
                stored_result['interpretation'] = result_copy.get('interpretation')

            if final_results:
                return next(iter(final_results.values()))

        else:
            logger.warning(f"No company found with ID {id}")
            return {}
    except asyncpg.PostgresError as e:
        logger.error(f"Database error occured: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch company details for company ID {id}: {str(e)}")
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
                logger.warning(f"{company_name} found")
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
                logger.warning(f"{company_apollo_id} found")
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
                logger.warning(f"{apollo_id} found")
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
            logger.info(results_list)
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
    
    #CHANGED
    query = "SELECT id FROM companies WHERE icp_score IS NULL"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            logger.info("Done fetching unscored companies")
            return results_list
    except Exception as e:
        logger.error(f"Failed to fetch unscored companies: {str(e)}")
        return []

#Store icp score in icp_scores table
async def store_icp_score(pool, company_id, age_score, employee_count_score,
                        funding_stage_score, keyword_score, contactability_score,
                        geography_score, total_score, category_breakdown, top_matches,
                        interpretation):
    category_breakdown = convert_sets(category_breakdown)
    category_breakdown_json = json.dumps(category_breakdown, indent=2)
    top_matches_json = json.dumps(top_matches, indent=2)
    logger.info(f"Storing ICP scores for company_id {company_id}...")
    #CHANGED
    query = """
    INSERT INTO icp_scores (
        company_id, age_score, employee_count_score, funding_stage_score, keyword_score,
        contactability_score, geography_score, total_score, category_breakdown, top_matches,
        interpretation
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
    )
    """
    async with pool.acquire() as conn:
        await conn.execute(query, company_id, age_score, employee_count_score,
                        funding_stage_score, keyword_score, contactability_score,
                        geography_score, total_score, category_breakdown_json, top_matches_json,
                        interpretation)
    logger.info("Data stored")
    return

#Store icp score in icp_score column in companies table. Changes status to mcp if score >= 70
async def update_company_icp_score(pool, company_id: int, total_score: float):
    logger.info(f"Updating icp_score for company_id {company_id} to {total_score}")

    # Update both icp_score and status (conditionally)
    query = """
        UPDATE companies
        SET icp_score = CAST($1 AS numeric(4,1)),
            status = CASE
                        WHEN $1 > 69 THEN 'mql'
                        ELSE status
                     END
        WHERE id = $2
    """

    async with pool.acquire() as conn:
        await conn.execute(query, float(total_score), company_id)

    logger.info("Company icp_score and status updated (if applicable)")


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
        x = await fetch_companies()
        print(x)
    asyncio.run(main())