import asyncio
import asyncpg
import logging
import os
from dotenv import load_dotenv
from services.db_service import *
from scoring_module.icp_scoring import ICPScorer
from utils.icp import icp

load_dotenv(override=True)
DB_URL = os.getenv("MOCK_DATABASE_URL")
#DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

CONCURRENCY_LIMIT = 50

#==============5. SCORING================
#Fetch unscored companies
async def score_and_store_company(pool, company_id, sempahore):
        async with sempahore:
        #unscored_company_id_list = await company_is_unscored(pool)    

        #Fetch company details
        #for company_id_info in unscored_company_id_list:
            #company_id = company_id_info.get("id")
            company_details = await fetch_company_details(company_id)
            org_name = company_details.get("name", "")
            org_founded_year = company_details.get("founded_year", None)
            org_employee_count = company_details.get("estimated_num_employees", None)
            org_funding_stage = company_details.get("latest_funding_round", "")
            org_keywords = company_details.get("keywords", [])
            org_people = company_details.get("people", [])
            org_linkedin = company_details.get("linkedin_url", "")
            org_country = company_details.get("country", "")

            #Calculate total score
            scorer = ICPScorer(icp, org_name, org_founded_year, org_employee_count,
                               org_funding_stage, org_keywords, org_people, org_linkedin,
                               org_country)
            await scorer.log_scoring_start(org_name)

            #calulate_total_score returns a dict with task_level, specific_tasks and total_score
            scoring_data = await scorer.calculate_total_score()
            age_score = scoring_data.get("age_score", None)
            employee_count_score = scoring_data.get("employee_count_score", None)
            funding_stage_score = scoring_data.get("funding_stage_score", None)
            final_keywords_score = scoring_data.get("final_keywords_score", None)
            contactability_score = scoring_data.get("contactability_score", None)
            geography_score = scoring_data.get("geography_score", None)
            category_breakdown = scoring_data.get("category_breakdown", {})
            top_matches = scoring_data.get("top_matches", {})
            interpretation = scoring_data.get("interpretation")
            final_score = scoring_data.get("total_score") if scoring_data.get("total_score") else 0

            #Store icp score
            await store_icp_score(pool, company_id, age_score, employee_count_score,
                                  funding_stage_score, final_keywords_score, contactability_score,
                                  geography_score, final_score, category_breakdown, top_matches,
                                  interpretation)
            await update_company_icp_score(pool, company_id, final_score)

            logger.info("Done storing ICP scores")

async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        unscored_company_id_list = await company_is_unscored(pool) 
        company_ids = [c["id"] for c in unscored_company_id_list]
        print(company_ids)
        tasks = [score_and_store_company(pool, cid, semaphore) for cid in company_ids]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    

    