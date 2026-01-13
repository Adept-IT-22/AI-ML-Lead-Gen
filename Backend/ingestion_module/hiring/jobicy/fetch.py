import sys
import os
import re
import logging
import httpx
import asyncio
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords
from utils.job_roles import desirable_roles

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_URL = "https://jobicy.com/api/v2/remote-jobs"

async def fetch_jobs() -> Dict[str, Any]:
    """Fetch jobs from Jobicy API."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {API_URL}...")
            response = await client.get(API_URL, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Jobicy jobs: {str(e)}")
            return {}

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process Jobicy jobs."""
    logger.info("Starting Jobicy hiring ingestion...")
    
    data = await fetch_jobs()
    if not data or "jobs" not in data:
        logger.warning("No jobs found from Jobicy")
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = data["jobs"]
    logger.info(f"Fetched {len(raw_jobs)} jobs from Jobicy")

    # Filter for software development jobs
    relevant_jobs = []
    for job in raw_jobs:
        title = job.get("jobTitle", "")
        if any(role in title.lower() for role in desirable_roles):
            relevant_jobs.append(job)
            
    logger.info(f"Filtered to {len(relevant_jobs)} relevant software development jobs")

    # Take latest 10
    targets = relevant_jobs[:10]

    # CHECK IF ITS IN NORMALIZED_MASTER
    
    if not targets:
        return copy.deepcopy(fetched_hiring_data)

    # Prepare for AI extraction
    ids_urls_titles = {
        "ids": [str(job.get("id", "")) for job in targets],
        "urls": [job.get("url", "") for job in targets],
        "titles": [f"{job.get('jobTitle')} at {job.get('companyName')}. Description: {job.get('jobDescription', '')[:1000]}" for job in targets]
    }
    
    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} Jobicy jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed for Jobicy: {e}")

    # Build final result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Jobicy"
    llm_results["type"] = "hiring"

    for job in targets:
        llm_results["title"].append(job.get("jobTitle", ""))
        llm_results["link"].append(job.get("url", ""))
        llm_results["company_name"].append(job.get("companyName", ""))
        llm_results["article_date"].append(job.get("pubDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        llm_results["article_id"].append(str(job.get("id", "")))
        
        # Placeholders for AI fields
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"]:
                llm_results[key].append([])
            else:
                llm_results[key].append("")

    # Merge AI results if available
    if extracted_data:
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in extracted_data and len(extracted_data[key]) == len(targets):
                llm_results[key] = extracted_data[key]

    logger.info(f"Jobicy ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
