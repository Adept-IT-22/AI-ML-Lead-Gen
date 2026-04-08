import logging
import asyncio
import asyncpg
from utils.icp import icp
from scoring_module.icp_scoring import ICPScorer
from services.db_service import fetch_company_details, store_icp_score, update_company_icp_score, company_is_unscored

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Fetch unscored companies
async def score_and_store(pool, company_id, semaphore):
    async with semaphore: 

        #Fetch company details
        company_details = await fetch_company_details(company_id)
        if not company_details:
            logger.warning(f"No company details found for company id: {company_id}")
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
        scoring_data = await scorer.calculate_total_score()

        #Store icp score
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
        
        await store_icp_score(pool, company_id, age_score, employee_count_score,
                            funding_stage_score, final_keywords_score, contactability_score,
                            geography_score, round(final_score, 1), category_breakdown, top_matches,
                            interpretation)
        await update_company_icp_score(pool, company_id, round(final_score, 1))

async def main(pool: asyncpg.Pool):
    logger.info("Scoring companies...")

    #Use a semaphore to allow concurrent scoring of companies
    semaphore = asyncio.Semaphore(10)
    unscored_company_id_list = await company_is_unscored(pool)    
    company_ids = [c.get("id", "") for c in unscored_company_id_list]
    storing_tasks = [score_and_store(pool, c_id, semaphore) for c_id in company_ids]
    results = await asyncio.gather(*storing_tasks, return_exceptions=True)
    for company_id, result in zip(company_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Scoring failed for company_id={company_id}: {result}")

    logger.info("ICP Scoring Done")


if __name__ and "__main__":
    pass