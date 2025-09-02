import os
import logging
import asyncpg
from typing import List, Any, Tuple
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)
DB_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger()

company_query = """
        INSERT INTO companies (apollo_id, name, website_url, linkedin_url,
                    phone, founded_year, market_cap, annual_revenue, industries,
                    estimated_num_employees, keywords, organization_headcount_six_month_growth,
                    organization_headcount_twelve_month_growth, city, state, country, short_description,
                    total_funding, technology_names, icp_score, contacted_status, notes, created_at,
                    updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            """
#Store company data to database
async def store_to_db(
        data_to_store: List[Tuple[Any]],
        query: str
    )->bool: #True = it worked. False = it failed
    
    logger.info("Storing company data...")
    
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.executemany(query, data_to_store)               
        await conn.close()

        logger.info("Completed storing company data")
        return True

    except Exception as e:
        logger.error(f"Failed to store company data. {str(e)}")
        return False
