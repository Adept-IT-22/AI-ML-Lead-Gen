import json
import httpx
import aiofiles
import asyncio
import logging
import yappi
from typing import List, Dict, Any, Awaitable, Union, Callable
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data
from enrichment_module.organization_search import org_search as apollo_org_search
from enrichment_module.bulk_org_enrichment import bulk_org_enrichment 
from enrichment_module.people_search import people_search

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#This function pairs a name with a coroutine (if all goes well) or with an exception otherwise 
async def wrap(name: str, coroutine: Awaitable[Any] )->tuple[str, Union[Any, Exception]]:
    try:
        result = await coroutine 
        logger.info(f"Coroutine {name} done")
        return name, result
    except Exception as e:
        logger.error(f"Coroutine {name} failed with the exception: {str(e)}")
        return name, e

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

    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get()
        logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

    #2.2 ==========Normalize data ===============
        data_type = data.get("type")
        if isinstance(data, dict) and data_type == "event": 
            normalized_data= await normalize_event_data(data)

        elif isinstance(data, dict) and data_type == "funding":
            normalized_data = await normalize_funding_data(data)

        elif isinstance(data, dict) and data_type == "hiring":
            normalized_data = await normalize_hiring_data(data)

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
    
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            orgs_to_search = []
            searched_orgs = []

            for normalized_company in data_to_enrich_list:
                company_names = normalized_company.get("company_name", [])
                orgs_to_search.extend(company_names)

    #2.2 =======Organization Search to Get Org Website=========
            logger.info("Organizational search started...")

            searched_tasks = [apollo_org_search(client=client, company_name=name) for name in company_names]
            search_results = await asyncio.gather(*searched_tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed {result}")
                else:
                    searched_orgs.append(result)

            logger.info(f"Completed organization seach for {len(searched_orgs)} companies")

            async with aiofiles.open(f"org_search.txt", "a") as org_search_file:
                await org_search_file.write(json.dumps(searched_orgs[0], indent=2))

            logger.info("Completed organizational search")
    
    #2.3 ========Bulk Org Enrichment===========
            logger.info("Org Enrichment started...")
            enriched_orgs = []

            #Batch orgs in groups of 10
            searched_orgs_length = len(searched_orgs)
            for i in range(0, searched_orgs_length, 10):
                batch = searched_orgs[i: i+10]

            #EXtract websites from batch
            org_websites = []
            for org_data in batch:
                if 'organizations' in org_data and org_data['organizations']:
                    logger.info(f"Enriching {org_data.get("organizations")[0].get("name")}")
                    website = org_data.get('organizations')[0].get('website_url')
                    if website:
                        org_websites.append(website)
            
            if org_websites:
                try:
                    enriched_batch= await bulk_org_enrichment(client=client, company_websites=org_websites)
                    enriched_orgs.append(enriched_batch)
                except Exception as e:
                    logger.error(f"Failed bulk enrichment for bulk starting at index {i}")
            
            async with aiofiles.open("org_enrichment.txt", "w") as org_enrichment_file:
                await org_enrichment_file.write(json.dumps(enriched_orgs, indent=2))

            logger.info("Completed Org Enrichment")

    #2.4 ========People Search========
            logger.info("People Search started...")

            #Get org ids
            org_ids = []
            org_domains = []
            for orgs in enriched_orgs:
                org_data = orgs.get("organizations") #returns a list of dicts
                for each_org in org_data:
                    org_id = each_org.get("id")
                    org_ids.append(org_id)
                    org_domain = each_org.get("primary_domain")
                    org_domains.append(org_domain)

            logger.info(f"The org ids are {org_ids}")
            logger.info(f"The org domains are {org_domains}")

            #Call people search and get people's names and emails
            found_people_names = []
            found_people_numbers = []
            found_people_emails = []
            found_people_titles = []
            found_people_orgs = []
            searched_people = await people_search(client=client, org_ids=org_ids, org_domains=org_domains)
            logger.info(f"The people search results are: {searched_people}")
            for people in searched_people.get("people", []):
                found_people_names.append(people.get("name", ""))
                found_people_names.append(people.get("sanitized_phone", ""))
                found_people_emails.append(people.get("email", ""))
                found_people_titles.append(people.get("title", ""))
                found_people_orgs.append(people.get("employment_history")[0].get("organization_name", ""))

            found_people_details = {
                "names": found_people_names,
                "numbers": found_people_numbers,
                "emails": found_people_emails,
                "titles": found_people_titles,
                "orgs": found_people_orgs
            }

            async with aiofiles.open("people_search.txt", "w") as people_search_file:
                await people_search_file.write(json.dumps(found_people_details, indent=2))

            logger.info("Completed people Search")
    #==============4. STORAGE================



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

if __name__ == "__main__":
    logger.info("Application running....")
    asyncio.run(main())
    logger.info("Application Done")