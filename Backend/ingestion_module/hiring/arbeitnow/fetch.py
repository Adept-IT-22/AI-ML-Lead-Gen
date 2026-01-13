import sys
import os
import re
import logging
import httpx
import asyncio
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.job_roles import desirable_roles

# Add the Backend directory to sys.path to allow imports like 'utils' and 'ingestion_module'
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_URL = "https://www.arbeitnow.com/api/job-board-api"

async def fetch_jobs() -> Dict[str, Any]:
    """Fetch jobs from Arbeitnow API."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {API_URL}...")
            response = await client.get(API_URL, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Arbeitnow jobs: {str(e)}")
            return {}

async def main() -> Optional[Dict[str, Any]]:
    """Main function for Arbeitnow ingestion."""
    logger.info("Starting Arbeitnow hiring ingestion...")
    
    data = await fetch_jobs()
    if not data or "data" not in data:
        logger.warning("No data found from Arbeitnow API")
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = data["data"]
    logger.info(f"Fetched {len(raw_jobs)} jobs from Arbeitnow")

    # Filter for software development jobs
    relevant_jobs = []
    for job in raw_jobs:
        title = job.get("title", "")
        if any(role in title.lower() for role in desirable_roles):
            relevant_jobs.append(job)
            
    logger.info(f"Filtered to {len(relevant_jobs)} relevant software development jobs")

    # Limit to latest 10
    targets = relevant_jobs[:10]
    if not targets:
        return copy.deepcopy(fetched_hiring_data)

    # CHECK IF IT EXISTS IN NORMALIZED_MASTER

    # Prepare for AI extraction
    ids_urls_titles = {
        "ids": [job.get("slug", str(hash(job.get("url", "")))) for job in targets],
        "urls": [job.get("url", "") for job in targets],
        "titles": [f"{job.get('title')} at {job.get('company_name')}. Description: {job.get('description', '')[:1000]}" for job in targets]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} Arbeitnow jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI failed for Arbeitnow: {e}")

    # Build final result
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Arbeitnow"
    llm_results["type"] = "hiring"

    for job in targets:
        llm_results["title"].append(job.get("title", ""))
        llm_results["link"].append(job.get("url", ""))
        llm_results["company_name"].append(job.get("company_name", ""))
        llm_results["article_date"].append(datetime.now().strftime("%Y-%m-%d")) # API doesn't always have date
        llm_results["article_id"].append(job.get("slug", ""))
        
        # Placeholders
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"]:
                llm_results[key].append([])
            else:
                llm_results[key].append("")

    # Merge AI
    if extracted_data:
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in extracted_data and len(extracted_data[key]) == len(targets):
                llm_results[key] = extracted_data[key]

    logger.info(f"Arbeitnow ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
