import time
import httpx
import logging
import asyncio
from typing import Dict, Any
from config.apollo_config import headers as APOLLO_HEADERS
from helpers.apollo_rate_limiter import rate_limited_apollo_call

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ORGANIZATION_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_companies/search"

async def no_rate_limit_org_search(
        client: httpx.AsyncClient, 
        company_name: str, 
        api_url: str = ORGANIZATION_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:
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
        return response.json()
    
    except Exception as e:
        logger.error(f"Couldnt perform organization search for {company_name}: {str(e)}")
        return {"Error": str(e)}

async def org_search(
        client: httpx.AsyncClient, 
        company_name: str, 
        api_url: str = ORGANIZATION_SEARCH_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:

    return await rate_limited_apollo_call(no_rate_limit_org_search, client, company_name, api_url, headers)

if __name__ == "__main__":
    async def main():
        company_names = [
            "LiveGrow Bio",
            "REVEL Drinks",
            "KGD Architecture",
            "DevAlly",
            "Finerd",
            "Quilter",
            "Vulcan",
            "Nexcade",
            "Intangles",
            "Medeon",
            "Reo.Dev",
            "Interfere",
            "Chando",
            "TINGE",
            "Salus BioMed",
            "NanoPhoria",
            "Curadel Surgical Innovations",
            "Ona Therapeutics",
            "TORL BioTherapeutics",
            "CaptainPepe",
            "Block Street",
            "Jaagruk Bharat",
            "Curiouz",
            "Sitehop",
            "Tigris Data",
            "ConverJinn",
            "Ozi",
            "Forest",
            "Ms.Engineer",
            "Producers Midstream"
        ]

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:

            tasks = [org_search(client, company_name, ORGANIZATION_SEARCH_URL, APOLLO_HEADERS) for company_name in company_names]
            results = await asyncio.gather(*tasks)
            logger.info(f"Org search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())
