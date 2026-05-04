import os
import httpx
import asyncpg
import asyncio
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from orchestration.enrichment import search_for_people, enrich_people
from storage_module.people_storage import people_storage
from orchestration.outreach import main as outreach_main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_uncontacted_companies_without_people(pool: asyncpg.Pool) -> List[asyncpg.Record]:
    """Fetches uncontacted companies that currently have no associated people records."""
    logger.info("Fetching uncontacted companies with no people...")
    query = """
    SELECT c.apollo_id AS org_id, c.website_url AS org_domain
    FROM mock_companies c
    LEFT JOIN mock_people p ON c.apollo_id = p.organization_id
    WHERE p.id IS NULL AND c.contacted_status = 'uncontacted';
    """
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            logger.info(f"Found {len(results)} uncontacted companies with no people.")
            return results
    except Exception as e:
        logger.error(f"Error fetching uncontacted companies without people: {e}")
        return []

def format_companies_for_apollo(db_results: List[asyncpg.Record]) -> List[List[Dict[str, Any]]]:
    """Formats DB results into the nested structure expected by the enrichment module."""
    organizations = [
        {"id": row["org_id"], "primary_domain": row["org_domain"]} for row in db_results
    ]
    # search_for_people expects a list of bulk_enriched_orgs lists
    return [[{"organizations": organizations}]]

async def search_and_enrich_people(client: httpx.AsyncClient, bulk_org_payload: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Handles the search and enrichment of people based on organization data."""
    logger.info("Starting people discovery (search + enrichment)...")
    
    searched_people = await search_for_people(bulk_org_payload, client)
    
    if not searched_people or not searched_people.get("people"):
        logger.warning("No people found during search.")
        return {}
        
    enriched_people = await enrich_people(searched_people, client)
    return {
        "searched_people": searched_people,
        "enriched_people": enriched_people
    }

async def persist_discovered_contacts(discovery_results: Dict[str, Any]):
    """Stores the found and enriched people into the database."""
    if not discovery_results:
        return
        
    logger.info("Storing enriched people to database...")
    await people_storage(
        discovery_results["searched_people"], 
        discovery_results["enriched_people"]
    )

async def trigger_outreach_for_orgs(pool: asyncpg.Pool, org_ids: List[str]):
    """Triggers the outreach pipeline for the newly added contacts."""
    if not org_ids:
        return
        
    logger.info(f"Triggering outreach main process for {len(org_ids)} organizations...")
    await outreach_main(pool, organization_ids=org_ids)

async def find_missing_people(pool: asyncpg.Pool, client: httpx.AsyncClient):
    """Orchestrates the discovery and outreach pipeline for leads missing contacts."""
    # 1. Fetch
    db_results = await get_uncontacted_companies_without_people(pool)
    if not db_results:
        logger.info("No missing people to process.")
        return
        
    # 2. Format
    bulk_org_payload = format_companies_for_apollo(db_results)
    
    # 3. Find (Search + Enrich)
    discovery_results = await search_and_enrich_people(client, bulk_org_payload)
    
    # 4. Store
    await persist_discovered_contacts(discovery_results)
    
    # 5. Outreach triggered manually via separate process
    # org_ids = [row["org_id"] for row in db_results if row["org_id"]]
    # await trigger_outreach_for_orgs(pool, org_ids)
    
    logger.info("Finished processing missing people pipeline.")

if __name__ == "__main__":
    load_dotenv(override=True)
    DB_URL = os.getenv("MOCK_DATABASE_URL")

    async def main():
        print("Starting pipeline to discover and enrich missing leads...")
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                await find_missing_people(pool, client)
        print("Discovery execution complete.")
                
    asyncio.run(main())
