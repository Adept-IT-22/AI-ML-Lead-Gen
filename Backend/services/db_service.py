import os
import logging
import psycopg
from typing import List, Any, Tuple
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)
DB_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger()

#Store company data to database
async def store_to_db(
        company_data_to_store: List[Tuple[Any]]
    )->bool: #True = it worked. False = it failed
    
    logger.info("Storing company data...")
    query = """
            INSERT INTO companies (apollo_id, name, website_url, linkedin_url,
                        phone, founded_year, market_cap, annual_revenue, industries,
                        estimated_num_employees, keywords, organization_headcount_six_month_growth,
                        organization_headcount_twelve_month_growth, city, state, country, short_description,
                        total_funding, technology_names, icp_score, contacted_status, notes, created_at,
                        updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                """
    try:
        async with await psycopg.AsyncConnection.connect(conninfo=DB_URL) as conn:
            async with conn.cursor() as cur:
                await cur.executemany(query, company_data_to_store)               
            await conn.commit()

        logger.info("Completed storing company data")
        return True

    except Exception as e:
        logger.error(f"Failed to store company data. {str(e)}")
        return False
