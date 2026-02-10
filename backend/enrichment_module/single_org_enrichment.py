import time
import json
import httpx
import aiofiles
import logging
import asyncio
from typing import Dict, Any, List
from config.apollo_config import headers as APOLLO_HEADERS
from helpers.apollo_rate_limiter import rate_limited_apollo_call
from aiolimiter import AsyncLimiter

#Apollo allows 200 requests per minute
limiter = AsyncLimiter(max_rate=180, time_period=60)

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SINGLE_ORG_ENRICHMENT_URL = "https://api.apollo.io/api/v1/organizations/enrich"

async def no_rate_limit_single_org_enrichment(
        client: httpx.AsyncClient, 
        company_website: str, #primary_domain from enrichment results
        api_url: str = SINGLE_ORG_ENRICHMENT_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:
    logger.info(f"Performing single organization enrichment for {company_website}...")

    #Check if company websites is empty or > 10
    if not company_website:
        logger.warning("Company_wesbites in single org enrichment is empty")

    #Payload going into request body
    payload = {
        "domain": company_website,
    }

    try:
        #API call then check for errors
        response = await client.post(
            url=api_url, 
            headers=headers, 
            json=payload
        )
        response.raise_for_status()

        logger.info(f"Completed single organization search for {company_website}")
        return response.json()
    
    except Exception as e:
        logger.error(f"Couldnt perform single organization search for {company_website}: {str(e)}")
        return {"Error": str(e)}

async def single_org_enrichment(
        client: httpx.AsyncClient, 
        company_website: str, #primary_domain from enrichment results
        api_url: str = SINGLE_ORG_ENRICHMENT_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:

    return await rate_limited_apollo_call(no_rate_limit_single_org_enrichment, client, company_website, api_url, headers, limiter=limiter)

if __name__ == "__main__":
    async def main():
        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await single_org_enrichment(client=client, company_website="eagle.org")
            print(results)

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())
