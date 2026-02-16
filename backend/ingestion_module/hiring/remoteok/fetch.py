"""
RemoteOK Jobs Fetcher
Fetches remote job listings from RemoteOK API.
"""
import re
import logging
import aiohttp
import asyncio
import copy
from datetime import datetime
from typing import List, Dict, Any, Optional
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

async def fetch_jobs() -> List[Dict[str, Any]]:
    """Fetch jobs from RemoteOK API."""
    headers = {"User-Agent": USER_AGENT}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"RemoteOK API returned {len(data)} items")
                        
                        # The first element in the list is often legal/metadata info
                        jobs = [item for item in data if "position" in item and "company" in item]
                        logger.info(f"Filtered down to {len(jobs)} valid jobs")
                        return jobs
                    except Exception as e:
                        logger.error(f"Failed to parse RemoteOK JSON: {str(e)}")
                        text = await response.text()
                        logger.debug(f"Response text start: {text[:200]}")
                        return []
                else:
                    logger.error(f"Failed to fetch RemoteOK jobs: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching RemoteOK jobs: {str(e)}")
            return []

def normalize_job_data(job: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize RemoteOK job data to our internal format."""
    return {
        "id": str(job.get("id", "")),
        "title": job.get("position", ""),
        "company": job.get("company", ""),
        "url": job.get("url", ""),
        "description": job.get("description", ""),
        "date": job.get("date", ""),
        "location": job.get("location", ""),
        "tags": job.get("tags", []),
        "apply_url": job.get("apply_url", "")
    }

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process RemoteOK jobs."""
    logger.info("Starting RemoteOK hiring ingestion...")
    
    raw_jobs = await fetch_jobs()
    if not raw_jobs:
        logger.warning("No jobs found from RemoteOK")
        return None

    logger.info(f"Fetched {len(raw_jobs)} jobs from RemoteOK")

    # Filter for software/developer jobs 
    final_raw_jobs = []
    for job in raw_jobs:
        url = job.get("url", "")
        if not any(re.search(rf'\b{re.escape(keyword)}\b', url.lower()) for keyword in software_dev_keywords):
            continue
        else:
            final_raw_jobs.append(job)
            
    logger.info("Filtered out %s non-sware jobs. %s left", (len(final_raw_jobs) - len(raw_jobs)), len(final_raw_jobs))
    processed_jobs = [normalize_job_data(job) for job in final_raw_jobs]
    
    ids_urls_titles = {
        "ids": [job["id"] for job in processed_jobs],
        "urls": [job["url"] for job in processed_jobs],
        "titles": [f"{job['title']} at {job['company']}" for job in processed_jobs]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(processed_jobs)} job postings to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"Failed to extract AI content from RemoteOK data: {str(e)}")

    # Build result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "remoteok"
    llm_results["type"] = "hiring"

    for job in processed_jobs:
        llm_results["title"].append(job["title"])
        llm_results["link"].append(job["url"])
        llm_results["company_name"].append(job["company"])
        llm_results["article_date"].append(job["date"])
        llm_results["article_id"].append(job["id"])
        
        # Basic location parsing
        llm_results["city"].append("") # RemoteOK often just says "Remote" or "Worldwide"
        llm_results["country"].append(job["location"]) # Often contains "Remote" or region

    # Merge LLM data
    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list):
                llm_results[key] = value_list

    logger.info("RemoteOK ingestion completed")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
