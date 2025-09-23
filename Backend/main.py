import json
import httpx
import aiofiles
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import yappi
from flask import Flask, jsonify, request
from flask_cors import CORS
from decimal import Decimal
from typing import List, Dict, Any, Awaitable, Union, Callable

from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
from utils.db_queries import *
from utils.data_normalization import *
from utils.icp import icp
from services.db_service import *
from services.email_sending import *
from services.sendgrid_webhook import *
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data
from enrichment_module.organization_search import org_search as apollo_org_search
from enrichment_module.bulk_org_enrichment import bulk_org_enrichment 
from enrichment_module.single_org_enrichment import single_org_enrichment
from enrichment_module.people_search import people_search
from enrichment_module.people_enrichment import people_enrichment
from scoring_module.icp_scoring import *
from helpers.helpers import *

# Configure logging before creating Flask app
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
file_handler = RotatingFileHandler(
    "main_log.log",
    maxBytes=10000000,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)
logger.addHandler(console_handler)

#DB_URL = os.getenv("DATABASE_URL")
DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

#Create Flask App
app = Flask(__name__)
app.logger.handlers = [] #Remove Flask's default logging
app.logger.propagate = True #Use our configured logger
CORS(app)

MAX_EMPLOYEE_COUNT = 20

async def run_ingestion_modules():
    #Each coroutine and it's name
    coroutines = [
        ("finsmes", finsmes_main()),
        ("tech_eu", tech_eu_main()),
        ("techcrunch", techcrunch_main()),
        ("hacker_news", hacker_news_main()),
        ("eventbrite", eventbrite_main())
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
        status = "SUCCESS ✅" if not isinstance(result, Exception) else "FAILED ❌"
        logger.info(f"{name}: {status}")

    return results

#===========PROGRAM'S MAIN CODE==============
@app.route('/run', methods=["GET", "POST"])
async def main():
    #==========1. INGESTION ================
    #=========1.1 Run the ingestion modules==========
    """
    Results below will be a dictionary of dictionaries i.e.
    {
        results = {
            "finmes": {
                "type": "funding",
                "source": "finsmes",
                etc.
            }
        }
    }
    """
    results = await run_ingestion_modules()

    #========1.2 Create queues===========
    ingestion_to_normalization_queue = asyncio.Queue()
    normalization_to_enrichment_queue = asyncio.Queue()

    #========1.3 Enqueue ingestion result values if they're not exceptions=====
    logger.info("Adding ingestion module results to queue 🚂")
    #Add {"finsmes": {}, "tech_eu": {}, "eventbrite": {}}
    for name, result in results.items():
        if not isinstance(result, Exception) and isinstance(result, dict) and result.get("type"):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")
        else:
            logger.error(f"Skipping {name} as its results were empty")

    #==============2. NORMALIZATION================
    #2.1 =========Fetch from queue============
    logger.info("Normalizing ingested data....")
    all_normalized_data = []

    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        while not ingestion_to_normalization_queue.empty():
            name, data = await ingestion_to_normalization_queue.get()
            logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

            # 2.2 ========== Normalize data ===============
            data_type = data.get("type")

            # Step 1: Normalize
            if data_type == "event":
                normalized_data = await normalize_event_data(data)
            elif data_type == "funding":
                normalized_data = await normalize_funding_data(data)
            elif data_type == "hiring":
                normalized_data = await normalize_hiring_data(data)
            else:
                logger.warning(f"Unknown data type: {data_type}")
                return

            # Step 2: Insert master (one row per dataset)
            for i, normalized_link in enumerate(normalized_data.get("link")):
                normalized_master_data_to_store = [
                    normalized_data.get("type", ""),
                    normalized_data.get("source", ""),
                    normalized_link,
                    normalized_data.get("title")[i] if normalized_data.get("title") and i < len(normalized_data.get("title", [])) else None,
                    normalized_data.get("city")[i] if normalized_data.get("city") and i < len(normalized_data.get("city", [])) else None,
                    normalized_data.get("country")[i] if normalized_data.get("country") and i < len(normalized_data.get("country", [])) else None,
                    normalized_data.get("tags")[i] if normalized_data.get("tags") and i < len(normalized_data.get("tags", [])) else []
                ]
                data_is_in_db = await is_data_in_db(pool, normalized_link)
                if data_is_in_db:
                    continue
                master_id = await store_in_normalized_master(normalized_master_data_to_store, pool)

                # Step 3: Insert children
                if data_type == "event":
                    event_data_to_store = [
                        master_id,
                        normalized_data.get("event_id")[i] if normalized_data.get("event_id") and i < len(normalized_data.get("event_id", [])) else None,
                        normalized_data.get("event_summary")[i] if normalized_data.get("event_summary") and i < len(normalized_data.get("event_summary", [])) else None,
                        normalized_data.get("event_is_online")[i] if normalized_data.get("event_is_online") and i < len(normalized_data.get("event_is_online", [])) else None,
                        normalized_data.get("event_organizer_id")[i] if normalized_data.get("event_organizer_id") and i < len(normalized_data.get("event_organizer_id", [])) else None
                    ]
                    try:
                        await store_in_normalized_events(event_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized events: {str(e)}")

                elif data_type == "funding":
                    funding_data_to_store = [
                        master_id,
                        normalized_data.get("company_name")[i] if normalized_data.get("company_name") and i < len(normalized_data.get("company_name", [])) else None,
                        normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers") and i < len(normalized_data.get("company_decision_makers", [])) else [],
                        normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position") and i < len(normalized_data.get("company_decision_makers_position", [])) else [],
                        normalized_data.get("funding_round")[i] if normalized_data.get("funding_round") and i < len(normalized_data.get("funding_round", [])) else None,
                        normalized_data.get("amount_raised")[i] if normalized_data.get("amount_raised") and i < len(normalized_data.get("amount_raised", [])) else None,
                        normalized_data.get("currency")[i] if normalized_data.get("currency") and i < len(normalized_data.get("currency", [])) else None,
                        normalized_data.get("investor_companies")[i] if normalized_data.get("investor_companies") and i < len(normalized_data.get("investor_companies", [])) else [],
                        normalized_data.get("investor_people")[i] if normalized_data.get("investor_people") and i < len(normalized_data.get("investor_people", [])) else [],
                    ]

                    try:
                        await store_in_normalized_funding(funding_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized funding: {str(e)}")

                elif data_type == "event":
                    event_data_to_store = [
                        master_id,
                        normalized_data.get("event_id")[i] if normalized_data.get("event_id") and i < len(normalized_data.get("event_id", [])) else None,
                        normalized_data.get("event_summary")[i] if normalized_data.get("event_summary") and i < len(normalized_data.get("event_summary", [])) else None,
                        normalized_data.get("event_is_online")[i] if normalized_data.get("event_is_online") and i < len(normalized_data.get("event_is_online", [])) else None,
                        normalized_data.get("event_organizer_id")[i] if normalized_data.get("event_organizer_id") and i < len(normalized_data.get("event_organizer_id", [])) else None
                    ]
                    try:
                        await store_in_normalized_events(event_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized events: {str(e)}")

                elif data_type == "hiring":
                    hiring_data_to_store = [
                        master_id,
                        normalized_data.get("company_name")[i] if normalized_data.get("company_name")[i] else None,
                        normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers")[i] else [],
                        normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position")[i] else [],
                        normalized_data.get("job_roles")[i] if normalized_data.get("job_roles")[i] else [],
                        normalized_data.get("hiring_reasons")[i] if normalized_data.get("hiring_reasons")[i] else []
                    ]
                    try:
                        await store_in_normalized_hiring(hiring_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized hiring data: {str(e)}")

            all_normalized_data.append(normalized_data)
            logger.info(f"Normalized {data_type} data from {name}")

    async with aiofiles.open("normalized.txt", "a") as file:
        await file.write(json.dumps(all_normalized_data, indent=2))

    logger.info("Done normalizing ingested data")

    #2.3 ==========Put In Normalization-Enrichment Queue===========
    logger.info("Adding normalized data to queue...")
    await normalization_to_enrichment_queue.put(all_normalized_data)
    logger.info(f"Done adding {len(all_normalized_data)} normalized items to queue")

    #==============3. ENRICHMENT================
    #2.1 =========Fetch from queue============
    logger.info("Enriching normalized data....")
    while not normalization_to_enrichment_queue.empty():
        data_to_enrich_list = await normalization_to_enrichment_queue.get()
        logger.info(f"Fetched {len(data_to_enrich_list)} items from normaliztion_to_enrichment queue.")
    
    #2.2 =======Organization Search to Get Org Website=========
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            set_of_orgs_to_search = set()
            searched_orgs = []

            for normalized_company in data_to_enrich_list:
                company_names = normalized_company.get("company_name", [])

    # ==========Check if company exists in DB before enriching=========
                for each_company in company_names:
                    lowercase_company = each_company.lower()
                    company_is_in_db = await is_company_in_db(company_name=lowercase_company)
                    if not company_is_in_db:
                        set_of_orgs_to_search.add(each_company)

            logger.info("Organizational search started...")

            orgs_to_search = list(set_of_orgs_to_search)
            searched_tasks = [apollo_org_search(client=client, company_name=name) for name in orgs_to_search]
            search_results = await asyncio.gather(*searched_tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed {result}")
                else:
                    searched_orgs.append(result)

            logger.info(f"Completed organization seach for {len(searched_orgs)} companies")

            async with aiofiles.open(f"org_search.txt", "a") as org_search_file:
                await org_search_file.write(json.dumps(searched_orgs, indent=2))

            logger.info("Completed organizational search")
    
    #2.3 ========Bulk Org Enrichment===========
            logger.info("Bulk Org Enrichment started...")
            bulk_enriched_orgs = []

            #Batch orgs in groups of 10
            searched_orgs_length = len(searched_orgs)
            for i in range(0, searched_orgs_length, 10):
                batch = searched_orgs[i: i+10]

                #Extract websites from batch
                bulk_org_websites = []
                for bulk_org_data in batch:
                    if 'organizations' in bulk_org_data and bulk_org_data['organizations']:
                        logger.info(f"Enriching {bulk_org_data.get('organizations')[0].get('name')}")
                        website = bulk_org_data.get('organizations')[0].get('website_url')
                        if website:
                            bulk_org_websites.append(website)
                
                #Perform enrichment on the batch
                if bulk_org_websites:
                    try:
                        bulk_enriched_batch= await bulk_org_enrichment(client=client, company_websites=bulk_org_websites)
                        bulk_enriched_orgs.append(bulk_enriched_batch)
                    except Exception as e:
                        logger.error(f"Failed bulk enrichment for bulk starting at index {i}: {str(e)}")
            
            async with aiofiles.open("bulk_org_enrichment.txt", "w") as bulk_org_enrichment_file:
                await bulk_org_enrichment_file.write(json.dumps(bulk_enriched_orgs, indent=2))

            logger.info("Completed Bulk Org Enrichment")

    #2.4 ========Single Org Enrichment===========
            logger.info("Single Org Enrichment started...")

            try:
                single_enriched_orgs = []
                if not bulk_enriched_orgs:
                    logger.error("No bulk enriched orgs")
                    return jsonify({"Error": "No bulk enriched orgs"})
                for single_org in bulk_enriched_orgs[0].get("organizations"):
                    org_domain = single_org.get("primary_domain")
                    single_enriched_org = await single_org_enrichment(client=client, company_website=org_domain)
                    single_enriched_orgs.append(single_enriched_org)
            except Exception as e:
                logger.error(f"Single enrichment failed: {str(e)}")
                
            async with aiofiles.open("single_org_enrichment.txt", "w") as single_org_enrichment_file:
                await single_org_enrichment_file.write(json.dumps(single_enriched_orgs, indent=2))

            logger.info("Completed Single Org Enrichment")
    
    #2.5 ========People Search========
            logger.info("People Search started...")

            #Get org ids
            org_ids = []
            org_domains = []
            for orgs in bulk_enriched_orgs:
                org_data = orgs.get("organizations") #returns a list of dicts
                for each_org in org_data:
                    org_id = each_org.get("id")
                    org_ids.append(org_id)
                    org_domain = each_org.get("primary_domain")
                    org_domains.append(org_domain)
            
            searched_people = await people_search(client=client, org_ids=org_ids, org_domains=org_domains)

            async with aiofiles.open("people_search.txt", "w") as people_search_file:
                await people_search_file.write(json.dumps(searched_people, indent=2))

            logger.info("Completed people Search")

    #2.6 ============People Enrichment=============
            logger.info("People Enrichment started....")

            enriched_people = []

            #Get user id's and names
            people_to_enrich = searched_people.get("people", [])
            for person in people_to_enrich:
                user_id = person.get("id", "")
                user_name = person.get("name", "")

                #Call people enrichment API
                enriched_person = await people_enrichment(client=client, user_id=user_id, user_name=user_name)
                enriched_people.append(enriched_person)

            async with aiofiles.open("people_enrichment.txt", "w") as people_enrichment_file:
                await people_enrichment_file.write(json.dumps(searched_people, indent=2))

            logger.info("Completed people enrichment")

    #==============4. STORAGE================
    logger.info("Storing data....")

    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        #=============Company Data Storage=============
        company_data_to_store = []

        searched_organizations = [orgs[0] for dictionary in searched_orgs if (orgs := dictionary.get("organizations"))]
        bulk_enriched_organizations = bulk_enriched_orgs[0].get("organizations", [])
        single_enriched_organizations = [item.get("organization", []) for item in single_enriched_orgs]

        #Iterate over orgs. Zip will stop when shortest list ends preventing errors
        if searched_organizations and bulk_enriched_organizations and single_enriched_organizations:
            for searched_org, bulk_enriched_org, single_enriched_organization in zip(searched_organizations, bulk_enriched_organizations, single_enriched_organizations, strict=False):
                try:
                    #Get necessary data from org search 
                    headcount_six_month_growth = searched_org.get("organization_headcount_six_month_growth", "")
                    headcount_twelve_month_growth = searched_org.get("organization_headcount_twelve_month_growth", "")

                    #Get necessary data from bulk enriched orgs
                    apollo_id = bulk_enriched_org.get("id", "")
                    #Check if org is in DB
                    company_name = bulk_enriched_org.get("name", "")
                    website_url = bulk_enriched_org.get("website_url", "")
                    linkedin_url = bulk_enriched_org.get("linkedin_url", "")
                    phone = bulk_enriched_org.get("phone", "")
                    founded_year = bulk_enriched_org.get("founded_year", "")
                    market_cap = bulk_enriched_org.get("market_cap", "")
                    industries = bulk_enriched_org.get("industries", [])
                    estimated_num_employees = bulk_enriched_org.get("estimated_num_employees", "")
                    keywords = bulk_enriched_org.get("keywords", [])
                    city = bulk_enriched_org.get("city", "")
                    state = bulk_enriched_org.get("state", "")
                    country = bulk_enriched_org.get("country", "")
                    short_description = bulk_enriched_org.get("short_description", "")

                    #Get necessary data from single enriched orgs
                    total_funding = single_enriched_organization.get("total_funding", "")
                    technology_names = single_enriched_organization.get("technology_names", [])
                    annual_revenue_printed = single_enriched_organization.get("annual_revenue", "")
                    funding_events_list = single_enriched_organization.get("funding_events", [])
                    if funding_events_list:
                        latest_funding_round = funding_events_list[0].get("type") 
                        unclean_latest_funding_amount = funding_events_list[0].get("amount") 
                        latest_funding_amount = normalize_amount_raised(unclean_latest_funding_amount) if unclean_latest_funding_amount else None
                        latest_funding_currency = funding_events_list[0].get("currency") 
                    else:
                        try:
                            normalized_funding_data = await fetch_funding_details(pool, company_name)
                            latest_funding_round = normalized_funding_data.get("funding_round", "")
                            latest_funding_amount = safe_int(normalized_funding_data.get("amount_raised", "0"))
                            latest_funding_currency = normalized_funding_data.get("currency", "")
                        except Exception as e:
                            logger.error(f"Failed to fetch funding details for {company_name}: {str(e)}")
                            latest_funding_round = ""
                            latest_funding_amount = None
                            latest_funding_currency = ""

                    #Get data source (funding, events, hiring) from normalized data
                    company_data_source = None
                    for normalized_company_info in all_normalized_data:
                        normalized_names = normalized_company_info.get("company_name", [])
                        for normalized_name in normalized_names:
                            if normalized_name.lower() in company_name.lower() or company_name.lower() in normalized_name.lower():
                                company_data_source = normalized_company_info.get("type")
                                break

                    #Fix the source link fetch
                    try:
                        source_link_details = await fetch_source_link(pool, company_name)
                        source_link = source_link_details.get("link", "")
                    except Exception as e:
                        logger.error(f"Failed to fetch source link for {company_name}: {str(e)}")
                        source_link = ""

                    

                    #Ensure all numeric values use safe_int() or safe_decimal()
                    company_row = (
                        apollo_id, 
                        company_name, 
                        website_url, 
                        linkedin_url, 
                        phone,
                        safe_int(founded_year),
                        safe_decimal(market_cap), 
                        safe_decimal(annual_revenue_printed),
                        industries,
                        safe_int(estimated_num_employees),
                        keywords,
                        safe_decimal(headcount_six_month_growth),
                        safe_decimal(headcount_twelve_month_growth),
                        city,
                        state,
                        country,
                        short_description,
                        safe_decimal(total_funding),
                        technology_names,
                        None, #icp score placeholder  
                        None,  # notes
                        company_data_source,
                        latest_funding_round,
                        latest_funding_amount,
                        latest_funding_currency,
                        source_link
                    )

                    company_data_to_store.append(company_row)

                except Exception as e:
                    logger.error(f"Failed to process company data for storage: {str(e)}")
                    continue

        #Store company data in "companies" database
        if company_data_to_store:
            await store_to_db(data_to_store=company_data_to_store, query=company_query, company_or_people="company")
        else:
            logger.warning("No companies to store ❌")

        #==============People Data Storage=================
        people_data_to_store = []

        people_search_data = searched_people.get("people", [])
        people_enrichment_data = enriched_people

        if people_search_data and people_enrichment_data:
            for person_search_data, person_enrichment_data in zip(people_search_data, people_enrichment_data):
                try:
                    #From people search API
                    apollo_user_id = person_search_data.get("id", "")
                    user_first_name = person_search_data.get("first_name", "")
                    user_last_name = person_search_data.get("last_name", "")
                    user_full_name = person_search_data.get("name", "")
                    user_linkedin_url = person_search_data.get("linkedin_url")
                    user_title = person_search_data.get("title", "")
                    user_email_status = person_search_data.get("email_status", "")
                    user_headline = person_search_data.get("headline", "")
                    user_organization_id = person_search_data.get("organization_id", "")
                    user_seniority = person_search_data.get("seniority", "")
                    user_departments = person_search_data.get("departments", [])
                    user_subdepartments = person_search_data.get("subdepartments", [])
                    user_functions = person_search_data.get("functions", [])

                    #From people enrichment API
                    user_email = person_enrichment_data.get("person", {}).get("email", "")
                    user_phone_number = None

                    #user_phone_number_data = person_enrichment_data.get("phone_numbers", [])
                    #if user_phone_number_data:
                        #user_phone_number = user_phone_number_data[0].get("sanitized_number", "")

                    people_row = (apollo_user_id, user_first_name, user_last_name, user_full_name,
                                    user_linkedin_url, user_title, user_email_status, user_headline,
                                    user_organization_id, user_seniority, user_departments, 
                                    user_subdepartments, user_functions, user_email, user_phone_number,
                                    None, #notes
                                ) 

                    people_data_to_store.append(people_row)

                except Exception as e:
                    logger.error(f"Failed to process people data for storage: {str(e)}")
                    continue

        if people_data_to_store:
            await store_to_db(data_to_store=people_data_to_store, query=people_query, company_or_people="people")
        else: 
            logger.error("No people data to store in db ❌")

    
    #==============5. SCORING================
    #Fetch unscored companies
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        unscored_company_id_list = await company_is_unscored(pool)    

        #Fetch company details
        for company_id_info in unscored_company_id_list:
            company_id = company_id_info.get("id")
            company_details = await fetch_company_details(company_id)
            org_name = company_details.get("name", "")
            org_founded_year = company_details.get("founded_year", None)
            org_employee_count = company_details.get("estimated_num_employees", None)
            org_funding_stage = company_details.get("latest_funding_round", "")
            org_funding_amount = company_details.get("latest_funding_amount", "")
            org_growth_velocity = company_details.get("organization_headcount_twelve_month_growth") if company_details.get("organization_headcount_twelve_month_growth") else company_details.get("organization_headcount_six_month_growth")
            org_keywords = company_details.get("keywords", [])
            org_people = company_details.get("people", [])
            org_phone = company_details.get("phone", "")
            org_linkedin = company_details.get("linkedin_url", "")
            org_website = company_details.get("website_url", "")
            org_country = company_details.get("country", "")

            #Calculate total score
            scorer = ICPScorer(icp, org_name, org_founded_year, org_employee_count,
                               org_funding_stage, org_funding_amount, org_growth_velocity,
                               org_keywords, org_people, org_phone, org_linkedin, org_website,
                               org_country)
            await scorer.log_scoring_start(org_name)
            total_icp_score = await scorer.calculate_total_score()

            #Store scored companies
            await store_icp_score(pool, org_name, company_id, total_icp_score)
            logger.info("Done storing ICP scores")

    #==============6. EMAIL================
    #logger.info("Sending emails...")
    #list_of_people_in_db = await fetch_people()

    ## Create one connection pool for all emails
    #async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        #for person in list_of_people_in_db:
            #try:
                #contacted_status = person.get("contacted_status", "")
                #persons_email = person.get("email", "")

                #if contacted_status != "uncontacted" or not persons_email:
                    #logger.info(f"Skipping {persons_email} - Status: {contacted_status}")
                    #continue

                ## Fetch company info
                #persons_company_apollo_id = person.get("organization_id", "")
                #persons_company = await fetch_company_by_apollo_id(persons_company_apollo_id)
                #if not persons_company:
                    #logger.warning(f"No company found for person {person.get('first_name')} with apollo ID {persons_company_apollo_id}")
                    #continue

                ## Prepare email data
                #data_source = persons_company.get("company_data_source", "")
                #email_to = persons_email
                #first_name = person.get("first_name")
                #company_name = persons_company.get("name")
                
                #logger.info(f"Preparing email for {first_name} ({email_to}) at {company_name}")

                ## Get extra info based on data source
                #if data_source == "funding":
                    #funding_round = persons_company.get("latest_funding_round")
                    #extra_info = "latest" if not funding_round or funding_round == "Other" else str(funding_round)
                #elif data_source == "hiring":
                    #hiring_area = await get_hiring_area(company_name, pool)
                    #extra_info = str(hiring_area) if hiring_area else "various areas"
                #else:
                    #logger.warning(f"Unknown data source {data_source} for {company_name}")
                    #continue

                ## Send individual email
                #response = await send_email(
                    #data_source=data_source,
                    #email_to=email_to,
                    #first_name=first_name,
                    #company_name=company_name,
                    #extra_info=extra_info
                #)

                ## Add delay between emails
                #if response and response.status_code == 202:
                    #logger.info(f"✅ Email sent successfully to {email_to}")
                    #await asyncio.sleep(1)  # Rate limiting - 1 second between emails
                #else:
                    #logger.error(f"❌ Failed to send email to {email_to} - Status: {response.status_code if response else 'No response'}")

            #except Exception as e:
                #logger.error(f"Failed to process email for {person.get('first_name', 'Unknown')}: {str(e)}")
                #continue

    #logger.info("Email sending complete")
    
    return jsonify({"success": "Main function done"}), 200

#Profiling Code
async def handle_profiling():
    profile_stats = yappi.get_func_stats()
    logger.info("========PROFILED STATS=======")
    async with aiofiles.open("yappi_stats.txt", "a") as file:
        await file.write(json.dumps(profile_stats, indent=2))
        await file.write("\n")

    profile_stats_filename = "profile_stats"
    profile_stats_file_type = "pstat"
    logger.info(f"Saving profile stats to file {profile_stats_filename}..")
    profile_stats.save(f"{profile_stats_filename}.{profile_stats_file_type}", type=profile_stats_file_type)
    logger.info("Profile saved")
    return

#Database API for fetching companies
@app.route('/fetch-companies', methods=["GET"])
async def fetch_company_data():
    company_data = await fetch_companies()
    if not company_data:
        return jsonify({"Error": "No company data found"}), 404
    return jsonify(company_data), 200

#Database API for fetching people
@app.route('/fetch-people', methods=["GET"])
async def fetch_people_data():
    people_data = await fetch_people()
    if not people_data:
        return jsonify({"Error": "No company data found"}), 404
    return jsonify(people_data), 200

#Database API for fetching company details
@app.route('/fetch-company-details/<id>', methods=["GET"])
async def fetch_company_details_data(id):
    company_details = await fetch_company_details(int(id))
    if not company_details:
        return jsonify({'Error': 'No company details found'}), 404
    return jsonify(company_details), 200

#Receive phone numbers from Apollo's People Enrichment API
#This method is dormant and not yet working.
@app.route('/apollo-phone-webhook', methods=["POST"])
async def receive_user_phone_number():
    logger.info("Receiving user phone number...")
    try:
        data = request.json
        if data:
            logger.info("Received phone number from Apollo webhook")
            logger.info(data)

            return jsonify({"status": "success", "message": "Phone number received"})

        else:
            return jsonify

    except Exception as e:
        logger.error(f"Failed to get phone number: {str(e)}")
        return jsonify({"status": "error", "message": "Internal Server Error"})

#Sendgrid webhook to receive data about emails sent
@app.route('/webhook', methods=["POST"])
async def sendgrid_events_webhook():
    logger.info("Fetching webhook event data...")
    events = request.json
    if not events:
        return jsonify({"Error": "No events received in request body"}), 400

    try:
        await update_contacted_status(events)
        logger.info("Successfully processed webhook events")
        return jsonify({"Success": "Done fetching webhook event data"}), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error during webhook processing: {str(e)}")
        return jsonify({"error": "Database update failed", "details": str(e)}), 500

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return {"Error": "An unexpected error occurred", "details": str(e)}, 500

#Endpoint to fetch events
@app.route('/events', methods=["GET"])
async def get_events():
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        try:
            events = await fetch_events(pool)
            return events
        except Exception as e:
            logger.error(f"Failed to fetch events: {str(e)}")
            return []


if __name__ == "__main__":
    logger.info("Application running....")
    app.run(debug=True)
    logger.info("Application Done")