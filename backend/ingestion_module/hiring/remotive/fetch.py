import sys
import os
import re
import logging
import httpx
import asyncio
import copy
from typing import List, Dict, Any, Optional
from utils.job_roles import desirable_roles

# Add the Backend directory to sys.path to allow imports like 'utils' and 'ingestion_module'
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"

async def fetch_jobs() -> Dict[str, Any]:
    """Fetch jobs from Remotive API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_URL, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Remotive jobs: {str(e)}")
            return {}

async def main() -> Dict[str, Any]:
    """Main function to fetch and process Remotive jobs."""
    logger.info("Starting Remotive hiring ingestion...")
    
    data = await fetch_jobs()
    if not data or "jobs" not in data:
        logger.warning("No jobs found from Remotive")
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = data["jobs"]
    logger.info(f"Fetched {len(raw_jobs)} jobs from Remotive")

    # Filter for software/developer jobs 
    # Remotive has a 'category' field, but keywords are safer as categories can be vague
    relevant_jobs = [] 
    for job in raw_jobs:

        # Retail only desired jobs
        if any(role in job.get("title").lower() for role in desirable_roles):
            relevant_jobs.append(job)

    logger.info(f"Filtered out {len(raw_jobs) - len(relevant_jobs)} non-sware jobs. {len(relevant_jobs)} left")
    
    # Prepare for AI extraction
    ids_urls_titles: Dict[str, List[str]] = {
        "ids": [],
        "urls": [],
        "titles": []
    }
    
    for job in relevant_jobs:
        # Remotive works with ID as int usually
        ids_urls_titles["ids"].append(str(job.get("id", "")))
        ids_urls_titles["urls"].append(job.get("url", ""))
        ids_urls_titles["titles"].append(job.get("title", ""))
        logger.info("Titles: %r", job.get("title"))

    extracted_data = {}
    if relevant_jobs:
        try:
            logger.info(f"Feeding {len(relevant_jobs)} job postings to AI extraction...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"Failed to extract AI content from Remotive data: {str(e)}")

    # Build result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Remotive"
    llm_results["type"] = "hiring"

    # Merge extracted data
    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list):
                llm_results[key] = value_list
        
        llm_results["title"] = extracted_data.get("title", ids_urls_titles["titles"])
        llm_results["link"] = extracted_data.get("article_link", ids_urls_titles["urls"])
        llm_results["article_id"] = extracted_data.get("article_id", ids_urls_titles["ids"])
        
        if "article_date" in extracted_data:
             llm_results["article_date"] = extracted_data["article_date"]
        else:
             llm_results["article_date"] = [job.get("publication_date", "") for job in relevant_jobs]

    logger.info("Remotive ingestion completed")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
