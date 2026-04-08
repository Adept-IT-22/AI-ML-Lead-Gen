import os
import copy
import json
import logging
import asyncio
import asyncpg
import uuid
from datetime import datetime
from typing import List, Any, Tuple, Dict
from dotenv import load_dotenv
from utils.db_queries import *
from utils.set_conversion import convert_sets

load_dotenv(verbose=True, override=True)


DB_URL = os.getenv("MOCK_DATABASE_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def add_company_note(company_id: int, note_text: str) -> Dict[str, Any]:
    """Adds a new note for a company."""
    logger.info(f"Adding note for company ID {company_id}")
    query = """
    INSERT INTO mock_company_notes (id, company_id, note)
    VALUES ($1, $2, $3)
    RETURNING id, company_id, note, created_at
    """
    note_id = str(uuid.uuid4())
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        result = await conn.fetchrow(query, note_id, company_id, note_text)
        await conn.close()
        if result:
            return dict(result)
        return {}
    except Exception as e:
        logger.error(f"Failed to add note: {str(e)}")
        if conn:
            await conn.close()
        return {}

async def delete_company_note(note_id: str) -> bool:
    """Deletes a note by its ID."""
    logger.info(f"Deleting note {note_id}")
    query = "DELETE FROM mock_company_notes WHERE id = $1"
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.execute(query, note_id)
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to delete note {note_id}: {str(e)}")
        if conn:
            await conn.close()
        return False

load_dotenv(verbose=True, override=True)


DB_URL = os.getenv("MOCK_DATABASE_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def initialize_db():
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        if conn:
            logger.info("Connection Made")
    except Exception as e:
        logger.error("Connection not made!")

#Fetches all companies from the database

async def fetch_companies_temporary():
    logger.info("Fetch companies from DB temporary")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        company_query = """
        SELECT 
            c.*, 
            p.full_name, p.title, p.email, p.linkedin_url,
            i.top_matches, i.interpretation
        FROM 
            mock_companies c 
        LEFT JOIN 
            mock_people p ON c.apollo_id = p.organization_id
        LEFT JOIN
            mock_icp_scores i ON c.id = i.company_id
        WHERE 
            c.name <> 'ICARUS Sports' 
        AND EXISTS (
            SELECT 1
            FROM mock_emails_sent es
            JOIN mock_people p2 ON es.recipient_id = p2.id
            WHERE p2.organization_id = c.apollo_id
        );
        
        """
        results = await conn.fetch(company_query)
        
        # 3. Close connection immediately after fetching data
        await conn.close()
        
        # 4. CONSOLIDATION LOGIC: Re-structure the flat 99 rows into 62 nested objects
        companies_map: Dict[str, Dict[str, Any]] = {}

        for record in results:
            # Convert asyncpg.Record to dict for easier manipulation
            record_dict = dict(record)
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


async def fetch_companies() -> List[Dict[str, Any]]:
    """
    Fetches all companies and their associated people in a single query (Eager Loading)
    and correctly consolidates the denormalized join results into a nested structure.
    """
    """
    Fetch all companies with associated people and notes in a single, scalable query.
    Uses JSON aggregation in Postgres to return one row per company.
    """
    logger.info("Fetching companies from DB...")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)

        company_query = """
        SELECT 
            c.*,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'full_name', p.full_name,
                    'title', p.title,
                    'email', p.email,
                    'linkedin_url', p.linkedin_url
                )) FILTER (WHERE p.id IS NOT NULL), '[]'::json
            ) AS people,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'id', n.id,
                    'note', n.note,
                    'created_at', n.created_at
                )) FILTER (WHERE n.id IS NOT NULL), '[]'::json
            ) AS notes,
            i.top_matches,
            i.interpretation
        FROM mock_companies c
        LEFT JOIN mock_people p ON c.apollo_id = p.organization_id
        LEFT JOIN mock_icp_scores i ON c.id = i.company_id
        LEFT JOIN mock_company_notes n ON c.id = n.company_id
        GROUP BY c.id, i.top_matches, i.interpretation;
        """

        results = await conn.fetch(company_query)

        # Convert asyncpg.Record -> dict for each company
        companies = []
        for r in results:
            d = dict(r)
            # Ensure JSON fields are parsed if they come back as strings
            for field in ['people', 'notes']:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except json.JSONDecodeError:
                        d[field] = []
            companies.append(d)

        logger.info(f"Done fetching and consolidating {len(companies)} companies.")
        return companies

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                logger.debug("Failed to close DB connection: %s", e)
        
async def fetch_people_from_company(organization_id: str)->List[Dict[str, str]]:
    logger.info(f"Fetching people from org id {organization_id}...")
    conn = await asyncpg.connect(dsn=DB_URL)
    
    people_query = "SELECT full_name, title, email, linkedin_url FROM mock_people WHERE organization_id = $1"
    people_results = await conn.fetch(people_query, organization_id)
    logger.info(f"Done fetching people from org id {organization_id}")
    await conn.close()
    return [dict(record) for record in people_results]


async def store_email(
        pool: asyncpg.Pool,
        recipient_id: int,
        company_id: int,
        subject: str,
        body: str,
        sequence_number: int
):
    logger.info("Storing email...")
    try:
        query_insert_email = """
            INSERT INTO mock_emails_sent 
            (recipient_id, company_id, subject, body, sequence_number)
            VALUES ($1, $2, $3, $4, $5)
            """

        query_update_company = """
                UPDATE mock_companies
                SET contacted_status = 'pending'
                WHERE id = $1
            """

        query_update_person = """
                UPDATE mock_people
                SET contacted_status = 'contacted'
                WHERE id = $1
            """
        async with pool.acquire(timeout=10.0) as conn:
            async with conn.transaction():
                await conn.execute(query_insert_email, recipient_id, company_id, subject, body, sequence_number)
                await conn.execute(query_update_company, company_id)
                await conn.execute(query_update_person, recipient_id)
        logger.info("Done storing email")
    except Exception as e:
        logger.exception("Failed to store email: %r", str(e))

#Fetch people from database

async def fetch_people()->List[Dict[str, Any]]:
    logger.info("Fetching people from DB...")
    try:
        conn = await asyncpg.connect(dsn=DB_URL) 
        query = "SELECT * FROM mock_people"
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


async def fetch_uncontacted_people(pool: asyncpg.Pool)->List:
    logger.info("Fetching uncontacted people from DB...")
    query = "SELECT id, first_name, organization_id, email FROM mock_people WHERE contacted_status = 'uncontacted' AND email IS NOT NULL AND email <> '' ORDER BY id LIMIT 10"

    try: 
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            uncontacted_people_organization_ids = [dict(result) for result in results]

        return uncontacted_people_organization_ids

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch uncontacted people", str(e))
        return []
    except Exception as e:
        logger.error(f"An unexpected error occured")
        return []

#Fetch company by ID
async def fetch_company_details(id: int) -> Dict[str, any]:
    """
    Fetch a single company by ID with its associated people and notes,
    using JSON aggregation to return one row per company.
    """
    logger.info(f"Fetching company with ID: {id}")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)

        query = """
        SELECT 
            c.*,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'full_name', p.full_name,
                    'title', p.title,
                    'email', p.email,
                    'linkedin_url', p.linkedin_url
                )) FILTER (WHERE p.id IS NOT NULL), '[]'::json
            ) AS people,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'id', n.id,
                    'note', n.note,
                    'created_at', n.created_at
                )) FILTER (WHERE n.id IS NOT NULL), '[]'::json
            ) AS notes,
            i.top_matches,
            i.interpretation
        FROM mock_companies c
        LEFT JOIN mock_people p ON c.apollo_id = p.organization_id
        LEFT JOIN mock_icp_scores i ON c.id = i.company_id
        LEFT JOIN mock_company_notes n ON c.id = n.company_id
        WHERE c.id = $1
        GROUP BY c.id, i.top_matches, i.interpretation;
        """

        result = await conn.fetchrow(query, id)

        await conn.close()

        if result:
            # Convert asyncpg.Record to dict
            d = dict(result)
            # Ensure JSON fields are parsed if they come back as strings
            for field in ['people', 'notes']:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except:
                        d[field] = []
            return d
        else:
            logger.warning(f"No company found with ID {id}")
            return {}

    except asyncpg.PostgresError as e:
        logger.error(f"Database error occurred: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch company details for company ID {id}: {str(e)}")
        return {}
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                pass

#Fetch company by apollo id

async def fetch_company_by_apollo_id(apollo_id: str)->Dict:
    logger.info(f"Fetching company with apollo ID {apollo_id}")
    query = "SELECT * FROM mock_companies WHERE apollo_id = $1 LIMIT 1"

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
    query = f"SELECT 1 FROM mock_companies WHERE LOWER(name) = LOWER($1) LIMIT 1"

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
    query = f"SELECT 1 FROM mock_companies WHERE apollo_id = $1 LIMIT 1"

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
    query = f"SELECT 1 FROM mock_people WHERE apollo_id = $1 LIMIT 1"

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
    query = f"SELECT 1 FROM mock_normalized_master WHERE link = $1 LIMIT 1"

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
    query = "UPDATE mock_people SET contacted_status = 'contacted' WHERE apollo_id = $1 RETURNING organization_id"

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
    query = "UPDATE mock_companies SET contacted_status = 'contacted' WHERE apollo_id = $1"

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
        query = "SELECT * FROM mock_normalized_master"
        results = await conn.execute(query)
    return results

#Get company from normalization_hiring table and return hiring area
async def get_hiring_area(company_name: str, pool) -> str:
    logger.info(f"Get hiring area for {company_name}")

    try:
        query = """
        SELECT job_roles
        FROM mock_normalized_hiring
        WHERE LOWER(company_name) = $1
        LIMIT 1
        """

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_name.lower())

            if not row:
                logger.warning(f"No hiring data found for {company_name}. Returning 'various areas'")
                return "various areas"

            job_roles = row["job_roles"]

            if not job_roles:
                return "various areas"

            return job_roles[0]

    except Exception as e:
        logger.exception(f"Couldn't get hiring area for {company_name}")
        return "various areas"

async def get_painpoints(company_name: str, pool, data_source: str) -> List[str]:
    """Retrieves pain points for a company from the specified data source table."""
    logger.info(f"Fetching painpoints for {company_name} from {data_source}")
    
    table = "mock_normalized_hiring" if data_source == "hiring" else "mock_normalized_funding"
    query = f"SELECT painpoints FROM {table} WHERE LOWER(company_name) = $1 LIMIT 1"
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_name.lower())
            if row and row["painpoints"]:
                # Painpoints are stored as List[str] in the database
                return row["painpoints"]
    except Exception as e:
        logger.error(f"Error fetching painpoints for {company_name}: {str(e)}")
    
    return []

    
#Get company funding details from normalized_funding

async def fetch_funding_details(pool: asyncpg.Pool, company_name: str)->Dict:
    logger.info(f"Fetching funding details for {company_name}")
    query = "SELECT funding_round, amount_raised, currency FROM mock_normalized_funding WHERE LOWER(company_name) = $1"

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
    query = "SELECT name FROM mock_companies WHERE latest_funding_round IS NULL AND latest_funding_amount IS NULL AND latest_funding_currency IS NULL"
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
            FROM mock_normalized_master m
            LEFT JOIN mock_normalized_events e ON m.id = e.master_id
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
    query = "SELECT keywords FROM mock_companies"
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
    
    
    query = "SELECT id FROM mock_companies WHERE icp_score IS NULL"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            if results:
                results_list = [dict(result) for result in results]
                logger.info("Done fetching unscored companies")
                return results_list
            else:
                logger.warning("No unscored companies found")
                return []

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
    
    query = """
    INSERT INTO mock_icp_scores (
        company_id, age_score, employee_count_score, funding_stage_score, keyword_score,
        contactability_score, geography_score, total_score, category_breakdown, top_matches,
        interpretation
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
    )
    ON CONFLICT (company_id)
    DO UPDATE SET
        age_score = EXCLUDED.age_score,
        employee_count_score = EXCLUDED.employee_count_score,
        funding_stage_score = EXCLUDED.funding_stage_score,
        keyword_score = EXCLUDED.keyword_score,
        contactability_score = EXCLUDED.contactability_score,
        geography_score = EXCLUDED.geography_score,
        total_score = EXCLUDED.total_score,
        category_breakdown = EXCLUDED.category_breakdown,
        top_matches = EXCLUDED.top_matches,
        interpretation = EXCLUDED.interpretation
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
        UPDATE mock_companies
        SET icp_score = CAST($1 AS numeric(4,1)),
            status = CASE
                        WHEN $1 > 69 THEN 'mql'
                        ELSE status
                     END
        WHERE id = $2
    """

    async with pool.acquire() as conn:
        await conn.execute(query, float(total_score), company_id)

    logger.info("Company icp_score and status updated")


async def fetch_people_by_ids(pool, ids: List[int]):
    if not ids:
        return []

    logger.info("Fetching people by ids...")
    query = "SELECT id, first_name, organization_id, email FROM mock_people WHERE id = ANY($1::int[])"
    async with pool.acquire() as conn:
        results = await conn.fetch(query, ids)

    return [dict(row) for row in results]


async def fetch_emails_sent(pool, company_id):
    logger.info("Fetching emails sent...")
    query = "SELECT * FROM mock_emails_sent WHERE company_id = $1"
    query = """
        SELECT
            e.subject, e.body, e.status, e.sent_at, 
            p.first_name,
            p.last_name
        FROM mock_emails_sent e
        JOIN mock_people p
            ON p.id = e.recipient_id
        WHERE e.company_id = $1; 
    """
    async with pool.acquire() as conn:
        emails = await conn.fetch(query, company_id)

    return [dict(email) for email in emails]

async def fetch_eligible_people(pool, organization_ids: List[str] = None)->List:
    if organization_ids == []:
        return []

    query = """
        SELECT 
            *
        FROM 
            mock_people
        WHERE
            subscribed = TRUE
        AND has_replied = FALSE
        AND times_contacted < 4
        AND (
            times_contacted = 0
            OR last_contacted_at <= now() - interval '7 days'
        )
    """
    
    params = []
    if organization_ids:
        query += " AND organization_id = ANY($1)"
        params.append(organization_ids)
        
    query += ";"
    
    try:
        async with pool.acquire() as conn:
            people = await conn.fetch(query, *params)
            return [dict(person) for person in people]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch uncontacted people", str(e))
        return []
    except Exception as e:
        logger.error(f"An unexpected error occured")
        return []

async def get_user_by_token(pool: asyncpg.Pool, token: str) -> Dict:
    """
    Fetch user details by unsubscribe token.
    Returns user dict or empty dict if not found.
    """
    logger.info(f"Fetching user by unsubscribe token...")
    query = """
        SELECT id, first_name, email, subscribed, unsubscribe_token
        FROM mock_people
        WHERE unsubscribe_token = $1
        LIMIT 1
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(query, token)
            
            if result:
                logger.info("User found by token")
                return dict(result)
            else:
                logger.warning("No user found with provided token")
                return {}
                
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching user by token: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error while fetching user by token: {str(e)}")
        return {}

async def unsubscribe_user(pool: asyncpg.Pool, token: str) -> bool:
    """
    Unsubscribe user by token. Returns True if successful, False otherwise.
    """
    logger.info(f"Attempting to unsubscribe user with token...")
    
    query = """
        UPDATE mock_people
        SET subscribed = FALSE,
            unsubscribed_at = NOW()
        WHERE unsubscribe_token = $1
        AND subscribed = TRUE
        RETURNING id, email
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(query, token)
            
            if result:
                logger.info(f"Successfully unsubscribed user: {result['email']} (ID: {result['id']})")
                return True
            else:
                logger.warning("No user found with provided token or user already unsubscribed")
                return False
                
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while unsubscribing user: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while unsubscribing user: {str(e)}")
        return False

async def add_company_note(company_id: int, note_text: str) -> Dict[str, Any]:
    """Adds a new note for a company."""
    logger.info(f"Adding note for company ID {company_id}")
    query = """
    INSERT INTO company_notes (id, company_id, note)
    VALUES ($1, $2, $3)
    RETURNING id, company_id, note, created_at
    """
    note_id = str(uuid.uuid4())
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        result = await conn.fetchrow(query, note_id, company_id, note_text)
        await conn.close()
        if result:
            return dict(result)
        return {}
    except Exception as e:
        logger.error(f"Failed to add note: {str(e)}")
        if conn:
            await conn.close()
        return {}

async def delete_company_note(note_id: str) -> bool:
    """Deletes a note by its ID."""
    logger.info(f"Deleting note {note_id}")
    query = "DELETE FROM company_notes WHERE id = $1"
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.execute(query, note_id)
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to delete note {note_id}: {str(e)}")
        if conn:
            await conn.close()
        return False

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

        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        #x = await fetch_company_details(160)
        #x = await fetch_company_by_apollo_id("671cebecf4941a02b6460f53")
            x = await get_hiring_area("14.ai", pool)

    asyncio.run(main())
