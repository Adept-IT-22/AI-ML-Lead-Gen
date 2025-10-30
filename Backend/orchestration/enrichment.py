import json
import httpx
import aiofiles
import asyncio
import logging
from typing import List, Dict
from services.db_service import is_company_in_db
from enrichment_module.people_search import people_search
from enrichment_module.people_enrichment import people_enrichment
from enrichment_module.bulk_org_enrichment import bulk_org_enrichment
from enrichment_module.single_org_enrichment import single_org_enrichment
from enrichment_module.organization_search import org_search as apollo_org_search

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# =========Fetch from queue============
async def fetch_from_normalization_to_enrichment_queue(normalization_to_enrichment_queue: asyncio.Queue)->List[Dict[str, str | List[str | List[str]]]]:
    while not normalization_to_enrichment_queue.empty():
        data_to_enrich_list = await normalization_to_enrichment_queue.get()
        logger.info(f"Fetched {len(data_to_enrich_list)} items from normaliztion_to_enrichment queue.")
        return data_to_enrich_list
    else:
        return []

    # =======Organization Search to Get Org Website=========

async def organization_search(data_to_enrich_list: List, client: httpx.AsyncClient)->List[Dict[str, str | Dict | List]]:
    if not data_to_enrich_list:
        logger.error("Org search failed. Normalization to enrichment queue was empty")
        return []

    #Get company names
    set_of_orgs_to_search = set()
    searched_orgs = []

    for normalized_company in data_to_enrich_list:
        company_names = normalized_company.get("company_name", [])

    # Check if company exists in DB first
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
    return searched_orgs

    # ========Bulk Org Enrichment===========

async def bulk_organization_enrichment(searched_orgs: List, client: httpx.AsyncClient)->List:
    logger.info("Bulk Org Enrichment started...")
    if not searched_orgs:
        logger.error("Bulk org enrichemnt failed. Empty input from org search")
        return []

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
                bulk_enriched_batch= await bulk_org_enrichment(client, bulk_org_websites)
                bulk_enriched_orgs.append(bulk_enriched_batch)
            except Exception as e:
                logger.error(f"Failed bulk enrichment for bulk starting at index {i}: {str(e)}")
    
    async with aiofiles.open("bulk_org_enrichment.txt", "w") as bulk_org_enrichment_file:
        await bulk_org_enrichment_file.write(json.dumps(bulk_enriched_orgs, indent=2))

    logger.info("Completed Bulk Org Enrichment")
    return bulk_enriched_orgs

    # ========Single Org Enrichment===========

async def single_organization_enrichment(bulk_enriched_orgs: list, client: httpx.AsyncClient)->List[Dict[str, str | Dict | List]]:
    logger.info("Single Org Enrichment started...")
    if not bulk_enriched_orgs:
        logger.error("Single org enrichemnt failed. Empty input from bulk org enrichment")
        return []

    try:
        single_enriched_orgs = []
        if not bulk_enriched_orgs:
            logger.error("No bulk enriched orgs")
            return {"Error": "No bulk enriched orgs"}
        for single_org in bulk_enriched_orgs[0].get("organizations"):
            org_domain = single_org.get("primary_domain")
            single_enriched_org = await single_org_enrichment(client=client, company_website=org_domain)
            single_enriched_orgs.append(single_enriched_org)
    except Exception as e:
        logger.error(f"Single enrichment failed: {str(e)}")
        
    async with aiofiles.open("single_org_enrichment.txt", "w") as single_org_enrichment_file:
        await single_org_enrichment_file.write(json.dumps(single_enriched_orgs, indent=2))

    logger.info("Completed Single Org Enrichment")
    return single_enriched_orgs

    # ========People Search========

async def search_for_people(bulk_enriched_orgs: List, client: httpx.AsyncClient)->Dict[str, str | Dict | List]:
    logger.info("People Search started...")
    if not bulk_enriched_orgs:
        logger.error("Single org enrichemnt failed. Empty input from bulk org enrichment")
        return []

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
    return searched_people

    # ============People Enrichment=============

async def enrich_people(searched_people: List, client: httpx.AsyncClient)->Dict[str, str | Dict | List]:
    logger.info("People Enrichment started....")
    if not searched_people:
        logger.error("People enrichment failed. Empty input from people search")
        return []

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
    return enriched_people
        
    # ============Main Function=============

async def main(
        normalization_to_enrichment_queue,
        enrichment_to_storage_queue,
          )->asyncio.Queue:
    logger.info("Enriching normalized data....")

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        data_to_enrich_list = await fetch_from_normalization_to_enrichment_queue(normalization_to_enrichment_queue)
        searched_orgs = await organization_search(data_to_enrich_list, client)
        bulk_enriched_orgs = await bulk_organization_enrichment(searched_orgs, client)
        single_enriched_orgs = await single_organization_enrichment(bulk_enriched_orgs, client)
        searched_people = await search_for_people(bulk_enriched_orgs, client)
        enriched_people = await enrich_people(searched_people, client)

    #Put above data in queue
    enrichment_to_storage_queue = asyncio.Queue()
    data_to_enqueue = {
        'searched_orgs': searched_orgs,
        'bulk_enriched_orgs': bulk_enriched_orgs,
        'single_enriched_orgs': single_enriched_orgs,
        'searched_people': searched_people,
        'enriched_people': enriched_people 
    }
    await enrichment_to_storage_queue.put(data_to_enqueue)

    logger.info('Enrichment done')
    return enrichment_to_storage_queue

if __name__ == "__main__":
    async def demo():
        n2eq = asyncio.Queue()
        e2sq = asyncio.Queue()
        normalized_data = [{'type': 'funding', 'source': ['FinSMEs'], 'title': [], 'link': ['https://www.finsmes.com/2025/10/socratix-ai-raises-4-1m-in-seed-funding.html'], 'article_date': ['2025-10-29'], 'company_name': ['socratix ai'], 'city': [], 'country': [], 'company_decision_makers': [['Riya Jagetia', 'Satya Vasanth Tumati']], 'company_decision_makers_position': [['Co-Founder', 'Co-Founder']], 'funding_round': ['Seed'], 'amount_raised': ['4099999'], 'currency': ['US Dollar'], 'investor_companies': [['Pear Vc', 'Y Combinator', 'Twenty Two Ventures', 'Transpose Platform Management']], 'investor_people': [[]], 'tags': [[]]}, {'type': 'funding', 'source': ['TechCrunch'], 'title': [], 'link': ['https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/'], 'article_date': ['2025-10-28'], 'company_name': ['mem0'], 'city': [], 'country': [], 'company_decision_makers': [['Taranjeet Singh', 'Deshraj Yadav']], 'company_decision_makers_position': [['Founder', 'Co-Founder And Cto']], 'funding_round': ['Series A'], 'amount_raised': ['24000000'], 'currency': ['US Dollar'], 'investor_companies': [['Basis Set Ventures', 'Kindred Ventures', 'Y Combinator', 'Peak Xv Partners', 'Github Fund']], 'investor_people': [['Dharmesh Shah', 'Scott Belsky', 'Olivier Pomel', 'Thomas Dohmke', 'Paul Copplestone', 'James Hawkins', 'Lukas Biewald', 'Brian Balfour', 'Philip Rathle', 'Jennifer Taylor', 'Lan Xuezhao']], 'tags': [[]]}]

        await n2eq.put(normalized_data)
        returned_queue = await main(n2eq, e2sq)

        print("THE RETURNED QUEUE DATA IS:")
        print(await returned_queue.get())

    asyncio.run(demo())

