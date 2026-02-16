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

API_URL = "https://himalayas.app/jobs/api"

async def fetch_jobs() -> Dict[str, Any]:
    """Fetch jobs from Himalayas API."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {API_URL}...")
            # Himalayas API might need a user agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await client.get(API_URL, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Himalayas jobs: {str(e)}")
            return {}

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process Himalayas jobs."""
    logger.info("Starting Himalayas hiring ingestion...")
    
    data = await fetch_jobs()
    if not data or "jobs" not in data:
        logger.warning("No jobs found from Himalayas")
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = data["jobs"]
    logger.info(f"Fetched {len(raw_jobs)} jobs from Himalayas")

    # Filter for software development jobs
    relevant_jobs = []
    for job in raw_jobs:
        # Himalayas provides title, description, and categories/tags
        title = job.get("title", "")

        if any(role in title.lower() for role in desirable_roles):
            relevant_jobs.append(job)

    logger.info(f"Filtered to {len(relevant_jobs)} relevant software development jobs")

    # Take latest 10 to avoid overwhelming AI
    targets = relevant_jobs[:10]

    # CHECK IF TARGETS EXIST IN NORMALIZED_MASTER
    
    if not targets:
        return copy.deepcopy(fetched_hiring_data)

    # Prepare for AI extraction
    ids_urls_titles = {
        "ids": [str(job.get("id", "")) for job in targets],
        "urls": [job.get("application_link", job.get("url", "")) for job in targets],
        "titles": [f"{job.get('title')} at {job.get('company_name')}. Description: {job.get('description', '')[:1000]}" for job in targets]
    }
    
    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} Himalayas jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed for Himalayas: {e}")

    # Build final result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Himalayas"
    llm_results["type"] = "hiring"

    # Populate basic info from targets
    for job in targets:
        llm_results["title"].append(job.get("title", ""))
        llm_results["link"].append(job.get("application_link", job.get("url", "")))
        llm_results["company_name"].append(job.get("company_name", ""))
        
        # Format date if available, else use today
        pub_date = job.get("pub_date", datetime.now().strftime("%Y-%m-%d"))
        llm_results["article_date"].append(pub_date)
        llm_results["article_id"].append(str(job.get("id", "")))
        
        # Placeholders for AI fields

    # Merge AI results if available
    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list) and len(value_list) == len(targets):
                llm_results[key] = value_list

    logger.info(f"Himalayas ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
