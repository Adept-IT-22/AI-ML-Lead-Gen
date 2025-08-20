import time
import httpx
import logging
import asyncio
from typing import Dict, Any
from config.apollo_config import headers as APOLLO_HEADERS

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ORGANIZATION_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_companies/search"

async def org_search(
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

if __name__ == "__main__":
    async def main():
        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await org_search(client=client, company_name="CoLoop")
            logger.info(f"Org search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())
