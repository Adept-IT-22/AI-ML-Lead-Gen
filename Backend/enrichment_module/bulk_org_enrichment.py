import time
import httpx
import logging
import asyncio
from typing import Dict, Any, List
from config.apollo_config import headers as APOLLO_HEADERS

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BULK_ORG_ENRICHMENT_URL = "https://api.apollo.io/api/v1/organizations/bulk_enrich"
RATE_LIMIT = 10

async def bulk_org_enrichment(
        client: httpx.AsyncClient, 
        company_websites: List[str], 
        api_url: str = BULK_ORG_ENRICHMENT_URL, 
        headers: Dict[str, str] = APOLLO_HEADERS
    )->Dict[str, Any]:
    logger.info(f"Performing bulk organization enrichment for {company_websites}...")

    #Check if company websites is empty or > 10
    if not company_websites:
        logger.warning("Company_wesbites array in Bulk org enrichment is empty")
    elif len(company_websites) > RATE_LIMIT:
        logger.warning(f"Company_websites in bulk org enrichment is > {RATE_LIMIT}")

    #Remove the www. at the start of the website
    clean_urls = []
    for website in company_websites:
        final_url = website.replace("http://", "").replace("https://", "").replace("www.", "")
        clean_urls.append(final_url) if final_url else None

    #Payload going into request body
    payload = {
        "domains": clean_urls,
    }

    try:
        #API call then check for errors
        response = await client.post(
            url=api_url, 
            headers=headers, 
            json=payload
        )
        response.raise_for_status()

        logger.info(f"Completed organization search for {company_websites}")
        return response.json()
    
    except Exception as e:
        logger.error(f"Couldnt perform organization search for {company_websites}: {str(e)}")
        return {"Error": str(e)}

if __name__ == "__main__":
    async def main():
        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await bulk_org_enrichment(client=client, company_websites=["http://www.coloop.ai", "www.microsoft.com"])
            logger.info(f"Org search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")
        return

    asyncio.run(main())
