import time
import httpx
import logging
import asyncio
from typing import Dict, Any, List
from config.apollo_config import headers as APOLLO_HEADERS
from helpers.apollo_rate_limiter import rate_limited_apollo_call

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ORGANIZATION_SEARCH_URL = "https://api.apollo.io/api/v1/organizations/search"

async def no_rate_limit_org_search(
        client: httpx.AsyncClient, 
        company_name: str | None= None, 
        organization_ids: List[str] | None = None,
        api_url: str = ORGANIZATION_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:
    
    if company_name:
        logger.info(f"Performing organization search for {company_name}...")

        #Payload going into request body
        payload = {
            "q_organization_name": company_name,
            "page": 1,
            "per_page": 1
        }
    
        try:
            #API call then check for errors
            response = await client.post(
                url=api_url, 
                headers=headers, 
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Completed organization search for {company_name}")
            result_json = response.json()
            result_json["search_query"] = company_name
            return result_json
        
        except Exception as e:
            logger.error(f"Couldnt perform organization search for {company_name}: {str(e)}")
            return {"Error": str(e), "search_query": company_name}

    elif organization_ids:
        logger.info(f"Performing organization search for organization ids: {organization_ids}...")

        #Payload going into request body
        payload = {
            "organization_ids": organization_ids,
            "page": 1,
            "per_page": 100
        }

        try:
            #API call then check for errors
            response = await client.post(
                url=api_url, 
                headers=headers, 
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Completed organization search")
            return response.json()
        
        except Exception as e:
            logger.error(f"Couldnt perform organization search: {str(e)}")
            return {"Error": str(e)}

async def org_search(
        client: httpx.AsyncClient, 
        company_name: str | None = None, 
        organization_ids: List[str] | None = None,
        api_url: str = ORGANIZATION_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:

    #if bool(company_name) == bool(organization_ids):
        #raise ValueError("Pass one of company name or organization ids")

    if company_name:
        return await rate_limited_apollo_call(no_rate_limit_org_search, client, company_name=company_name, api_url=api_url, headers=headers)
    elif organization_ids:
        return await rate_limited_apollo_call(no_rate_limit_org_search, client, organization_ids=organization_ids, api_url=api_url, headers=headers)
        

if __name__ == "__main__":
    async def main():
        #company_names = [
            #"LiveGrow Bio",
            #"REVEL Drinks",
        #]

        org_ids = ["632d58f35af1c200a4421ff1", "6605a2c9ec3b5304394889b4","6610cf7c242c9d01c711fa87", "54a1201f69702d97c1554802"]

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:

            #tasks = [org_search(client, company_name=company_name, api_url=ORGANIZATION_SEARCH_URL, headers=APOLLO_HEADERS) for company_name in company_names]
            #results = await asyncio.gather(*tasks)

            results = await org_search(client, organization_ids=org_ids)
            logger.info(f"Org search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())
