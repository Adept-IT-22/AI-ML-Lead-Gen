import json
import aiofiles
import asyncio
import logging
from httpx import AsyncClient
from typing import Dict, List
from config.apollo_config import headers as APOLLO_HEADERS

#This API is necessary to get user emails and numbers
API_URL = "https://api.apollo.io/api/v1/people/match"

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

WEBHOOK_URL = ""

async def people_enrichment(
      client: AsyncClient, 
      user_id: str,
      user_name: str,
      url: str = API_URL, 
      headers=APOLLO_HEADERS
    )->Dict:

    logger.info(f"People enrichment starting for {user_name} ...")

    params = {
      "reveal_personal_emails": True,
      #"reveal_phone_number": True,
      #"webhook_url": WEBHOOK_URL
    }

    payload = {"id": user_id}

    try:
      response = await client.post(
        url, 
        params=params, 
        json=payload, 
        headers=headers
      )

      logger.info(f"Completed people enrichment for {user_name}")

      return response.json()

    except Exception as e:
       logger.error(f"People enrichment failed: {str(e)}")

if __name__ == "__main__":
    async def main():
      async with AsyncClient(timeout=30.0) as client:
        await people_enrichment(
           client=client, 
           user_id="610c3e23d4d76a0001aa35b3",
           user_name="Charles Hayter"
                )

    asyncio.run(main())
      