import asyncio
import asyncpg

DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

#Fetch companies from companies where company_data_source is funding
async def fetch_companies(pool)->list:
    query = "SELECT name FROM companies WHERE company_data_source = 'funding'"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            result_list = [dict(result) for result in results]
            final_results = []
            for result in result_list:
                name = result.get("name", "")
                final_results.append(name)

            print(final_results)
            print("=============")
        return final_results
            
    except Exception as e:
        print(e)
        return []

#Check those companies in normalized_funding
async def check_in_normalized_funding(company_list, pool):
    # Get master_id from normalized_funding and then link from normalized_master
    funding_query = "SELECT master_id FROM normalized_funding WHERE company_name = $1"
    link_query = "SELECT link FROM normalized_master WHERE id = $1"
    update_query = "UPDATE companies SET source_link = $1 WHERE name = $2"

    try:
        async with pool.acquire() as conn:
            for company in company_list:
                print(company)
                master_id = await conn.fetchval(funding_query, company.lower())
                if master_id:
                    print(master_id)
                    link = await conn.fetchval(link_query, master_id)
                    if link:
                        await conn.execute(update_query, link, company)
                        print(link)
                        print(f"Updated {company} with link {link}")
    except Exception as e:
        print("Error:", e)
        return []


if __name__ == "__main__":
    async def main():
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            company_list = await fetch_companies(pool)
            await check_in_normalized_funding(company_list, pool)

    asyncio.run(main())