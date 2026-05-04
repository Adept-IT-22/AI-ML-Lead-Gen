import asyncio
import httpx
import logging
import json
import os
from dotenv import load_dotenv
from orchestration.enrichment import search_for_people

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_parallel_search():
    load_dotenv(override=True)
    
    # Mock bulk_enriched_orgs structure
    # This simulates 5 companies being found
    mock_bulk_enriched_orgs = [
        [
            {
                "organizations": [
                    {"id": "5ed22dc60fc35b0001c2574c", "name": "Canopy", "primary_domain": "usecanopy.com"},
                    {"id": "54a11233a69702d8aa192420", "name": "Remitly", "primary_domain": "remitly.com"},
                    {"id": "5e5823595432210001046bfd", "name": "Actble", "primary_domain": "actble.de"},
                    {"id": "60af29b91d84c20001fac584", "name": "Plaud", "primary_domain": "plaudlife.com"},
                    {"id": "5e5823595432210001046bfe", "name": "Cosonify", "primary_domain": "cosonify.com"}
                ]
            }
        ]
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("Starting test for parallel people search...")
        results = await search_for_people(mock_bulk_enriched_orgs, client)
        
        people = results.get("people", [])
        logger.info(f"Test complete. Total people found: {len(people)}")
        
        # Print first few results to verify
        for i, person in enumerate(people[:10]):
            logger.info(f"{i+1}. {person.get('first_name')} - {person.get('title')} at {person.get('organization', {}).get('name')}")

if __name__ == "__main__":
    asyncio.run(test_parallel_search())
