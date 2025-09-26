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
        company_details = await fetch_company_details(company_id)
        if not company_details:
            logger.warning(f"No company details found for id {company_id}")
            return
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
        task_level = scoring_data.get("task_level", "")
        specific_tasks = scoring_data.get("specific_tasks", {})
        final_score = scoring_data.get("total_score") if scoring_data.get("total_score") else 0

        #Store scored companies
        #await store_icp_score(pool, org_name, company_id, final_score, task_level, specific_tasks)
        logger.info(f"{org_name}, {company_id}, {final_score}, {task_level}, {specific_tasks}")
        logger.info(f"✅Done storing ICP score for {org_name}")

async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        #unscored_company_id_list = await company_is_unscored(pool) 
        #company_ids = [c["id"] for c in unscored_company_id_list]

        company_ids = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
        tasks = [score_and_store_company(pool, cid, semaphore) for cid in company_ids]
        await asyncio.gather(*tasks)

    #async with asyncpg.create_pool(dsn=DB_URL) as pool:
        #query = "SELECT * FROM companies"
        #async with pool.acquire() as conn:
            #results = await conn.fetch(query)
            #unscored_company_id_list = [dict(result) for result in results]
        ##Fetch company details
        #for company_id_info in unscored_company_id_list:
            #company_id = company_id_info.get("id")
            #company_details = await fetch_company_details(company_id)
            #org_name = company_details.get("name", "")
            #org_founded_year = company_details.get("founded_year", None)
            #org_employee_count = company_details.get("estimated_num_employees", None)
            #org_funding_stage = company_details.get("latest_funding_round", "")
            #org_keywords = company_details.get("keywords", [])
            #org_people = company_details.get("people", [])
            #org_linkedin = company_details.get("linkedin_url", "")
            #org_country = company_details.get("country", "")

            #logger.info(f"{company_id}, {org_name}, {org_country}")

            ##Calculate total score
            #scorer = ICPScorer(icp, org_name, org_founded_year, org_employee_count,
                               #org_funding_stage, org_keywords, org_people, org_linkedin,
                               #org_country)
            #await scorer.log_scoring_start(org_name)

            ##calulate_total_score returns a dict with task_level, specific_tasks and total_score
            #scoring_data = await scorer.calculate_total_score()
            #task_level = scoring_data.get("task_level", "")
            #specific_tasks = scoring_data.get("specific_tasks", {})
            #final_score = scoring_data.get("total_score") if scoring_data.get("total_score") else 0

            ##Store scored companies
            #await store_icp_score(pool, org_name, company_id, final_score, task_level, specific_tasks)
            #logger.info("Done storing ICP scores")
if __name__ == "__main__":
    asyncio.run(main())