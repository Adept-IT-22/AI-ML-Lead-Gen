import time
import json
import httpx
import logging
import asyncio
from typing import Dict, Any, List
from config.apollo_config import headers as APOLLO_HEADERS
from helpers.apollo_rate_limiter import rate_limited_apollo_call

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"

async def no_rate_limit_people_search(
        client: httpx.AsyncClient, 
        org_ids: List[str], 
        org_domains: List[str],
        api_url: str = PEOPLE_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:
    logger.info("Performing people search for %r...", org_domains)

    # Clean org_ids and org_domains to remove None values
    org_ids = [oid for oid in org_ids if oid]
    org_domains = [od for od in org_domains if od]

    payload = {
        "person_titles": [
        "ceo", "founder", "co-founder", "president", "owner", "partner",
        "cto", "chief product officer", "vp of engineering", "head of engineering", 
        "director of engineering", "vp of sales", "head of sales", "vp of marketing", "head of marketing",
        "vp of operations", "head of operations", "chief technological officer",
        "head of ai", "head of machine learning", "head of data science"
        ],
        "include_similar_titles": True,
        "person_seniorities": ["owner", "founder", "c_suite", "partner", "vp", "head", "director", "manager", "senior"],
        "contact_email_status": ["verified", "unverified", "likely_to_engage"],
        "organization_ids": org_ids,
        "q_organization_domains_list": org_domains,
        "page": 1,
        "per_page": 10
    }

    try:
        #API call then check for errors
        response = await client.post(
            url=api_url, 
            headers=headers, 
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Apollo API Error {response.status_code}: {response.text}")
            
        response.raise_for_status()

        logger.info(f"Completed people search")
        return response.json()
    
    except Exception as e:
        logger.error(f"Couldnt perform people search: {str(e)}")
        return {"Error": str(e)}

async def people_search(
        client: httpx.AsyncClient, 
        org_ids: List[str], 
        org_domains: List[str],
        api_url: str = PEOPLE_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:

    return await rate_limited_apollo_call(
        no_rate_limit_people_search, client, org_ids, org_domains, api_url, headers
        )
        

if __name__ == "__main__":
    async def main():
        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await people_search(
                client=client, 
                #org_ids=["5f50a22da4560d00e3eddf31"], 
                #org_domains=["nvidia.com"]
                org_ids = ["673106decb4dd60001ad5a7e"],
                org_domains=["smartsylvan.de"]
            )
            logger.info(f"People search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())