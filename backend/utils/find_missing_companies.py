import httpx
import asyncpg
import asyncio
from typing import List
from enrichment_module.organization_search import org_search
from orchestration.enrichment import organization_search, bulk_organization_enrichment, single_organization_enrichment
from storage_module.company_storage import company_storage

async def find_missing_companies(pool, client, organization_ids: List[str]):
    #Perform org search
    searched_orgs = await organization_search(organization_ids, client)
    
    #Perform bulk enrichment
    bulk_enriched_orgs = await bulk_organization_enrichment(searched_orgs, client)
    
    #Perform single org enrichment
    single_enriched_orgs = await single_organization_enrichment(bulk_enriched_orgs, client)
    
    #Store company data
    bulk_enriched_orgs = bulk_enriched_orgs[0] #Because bulk enriched orgs is a list within a list
    await company_storage(
        pool, 
        all_normalized_data=[], 
        searched_orgs=searched_orgs,
        bulk_enriched_orgs=bulk_enriched_orgs,
        single_enriched_orgs=single_enriched_orgs
        )

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    DB_URL = os.getenv("MOCK_DATABASE_URL")

    async def main():
        print("Running...")
        org_ids = ["632d58f35af1c200a4421ff1", "6605a2c9ec3b5304394889b4","6610cf7c242c9d01c711fa87", "54a1201f69702d97c1554802"]
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                missing_companies = await find_missing_companies(pool, client, org_ids)
                print("Missing companies:\n")
                print(missing_companies)
    asyncio.run(main())