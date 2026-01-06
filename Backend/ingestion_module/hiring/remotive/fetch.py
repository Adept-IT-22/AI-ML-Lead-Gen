"""
Remotive Jobs Fetcher
Fetches remote job listings from Remotive API.
"""
import re
import logging
import httpx
import asyncio
import copy
from typing import List, Dict, Any, Optional
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

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process Remotive jobs."""
    logger.info("Starting Remotive hiring ingestion...")
    
    data = await fetch_jobs()
    if not data or "jobs" not in data:
        logger.warning("No jobs found from Remotive")
        return None

    raw_jobs = data["jobs"]
    logger.info(f"Fetched {len(raw_jobs)} jobs from Remotive")

    # Filter for software/developer jobs 
    # Remotive has a 'category' field, but keywords are safer as categories can be vague
    relevant_jobs = []
    for job in raw_jobs:
        # Check title, category, and url
        text_to_check = (job.get("title", "") + " " + job.get("category", "") + " " + job.get("url", "")).lower()
        if any(re.search(rf'\b{re.escape(keyword)}\b', text_to_check) for keyword in software_dev_keywords):
             relevant_jobs.append(job)
            
    logger.info(f"Filtered out {len(raw_jobs) - len(relevant_jobs)} non-sware jobs. {len(relevant_jobs)} left")
    
    # Prepare for AI extraction
    ids_urls_titles = {
        "ids": [],
        "urls": [],
        "titles": []
    }
    
    for job in relevant_jobs:
        # Remotive works with ID as int usually
        ids_urls_titles["ids"].append(str(job.get("id", "")))
        ids_urls_titles["urls"].append(job.get("url", ""))
        ids_urls_titles["titles"].append(job.get("title", ""))

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
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "company_name", "city", "country"]:
            if key in extracted_data:
                llm_results[key] = extracted_data[key]
        
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
