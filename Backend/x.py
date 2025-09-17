#Check if company has funding details. if not, put data from normalized_funding
from services.db_service import *
import asyncio
import asyncpg

DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

#Check if companies have funding_details
async def get_companies_with_no_funding_details(pool):
    companies_with_no_funding_details = await return_companies_with_no_funding_details(pool)
    print(companies_with_no_funding_details)

    #Get funding details from normalized_data
    for company in companies_with_no_funding_details:
        funding_details = await fetch_funding_details(pool, company)

        #Store in companeies db
        if funding_details:
            await store_funding_data_in_companies_db(pool, company, funding_details)
        else:
            continue

async def store_funding_data_in_companies_db(pool, company_name, funding_details):
    print(f"Storing for {company_name}")
    query = "UPDATE companies SET latest_funding_round = $1, latest_funding_amount = $2, latest_funding_currency = $3 WHERE name = $4"

    try:
        async with pool.acquire() as conn:
            latest_funding_round = funding_details.get("funding_round", None)
            latest_funding_amount = funding_details.get("amount_raised", None)
            latest_funding_currency = funding_details.get("currency", None)
            response = await conn.execute(
                query, 
                latest_funding_round, 
                latest_funding_amount, 
                latest_funding_currency, 
                company_name
                )
            print(f"{company_name} stored. Reponse is {response}")

    except Exception as e:
        print(f"Failed to store: {str(e)}")



if __name__ == "__main__":
    async def main():
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            print("....")
            await get_companies_with_no_funding_details(pool)

    asyncio.run(main())


