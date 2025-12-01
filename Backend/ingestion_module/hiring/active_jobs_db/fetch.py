import logging
import httpx
import copy
import asyncio
import os
from typing import List, Dict, Any, Optional
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction

logger = logging.getLogger(__name__)

# API Configuration
API_HOST = "active-jobs-db.p.rapidapi.com"
API_URL = "https://active-jobs-db.p.rapidapi.com/active-ats-7d"

# Methodology: Search for remote Software jobs in target regions
SEARCH_QUERY = "Software"
TARGET_REGIONS = ["Germany", "Poland", "Switzerland", "Ireland", "Netherlands", "Kenya"]
LOCATION_FILTER = " OR ".join([f'"{region}"' for region in TARGET_REGIONS])

async def fetch_jobs_from_api(client: httpx.AsyncClient, query: str, location_filter: str) -> List[Dict]:
    """Fetches jobs from Active Jobs DB RapidAPI."""
    headers = {
        "x-rapidapi-key": os.getenv("RAPID_API_KEY", ""),
        "x-rapidapi-host": API_HOST
    }
    
    params = {
        "title_filter": query,
        "location_filter": location_filter,
        "remote": "true",
        "include_ai": "true",
        "include_li": "true",
        "limit": "100",
        "offset": "0"
    }

    logger.info(f"Fetching Active Jobs DB data for '{query}' in locations: {location_filter}...")
    
    try:
        response = await client.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API returned {len(data) if isinstance(data, list) else 'unknown'} jobs")
        
        if 'x-ratelimit-jobs-remaining' in response.headers:
            logger.info(f"Jobs credits remaining: {response.headers['x-ratelimit-jobs-remaining']}")
        
        return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error fetching Active Jobs DB data: {str(e)}")
    
    return []

async def main() -> Optional[Dict[str, Any]]:
    logger.info("Starting Active Jobs DB ingestion...")
    start_time = asyncio.get_running_loop().time()
    
    all_jobs = []
    
    async with httpx.AsyncClient() as client:
        jobs = await fetch_jobs_from_api(client, SEARCH_QUERY, LOCATION_FILTER)
        all_jobs.extend(jobs)

    if not all_jobs:
        logger.warning("No jobs found from Active Jobs DB.")
        return None

    # Prepare data for optional LLM extraction
    ids_urls_titles = {
        "ids": [job.get("id", "") for job in all_jobs],
        "urls": [job.get("url", "") for job in all_jobs],
        "titles": [job.get("title", "") for job in all_jobs]
    }

    extracted_data = {}
    if os.getenv("GEMINI_API_KEY"):
        try:
            logger.info("Feeding Active Jobs DB data to LLM for further extraction...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            logger.info("Continuing with API data only (API already includes AI-enriched fields)")
    else:
        logger.info("GEMINI_API_KEY not found. Skipping LLM extraction (API already has AI-enriched fields)")

    # Transform to standard structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Active Jobs DB"

    for job in all_jobs:
        llm_results["title"].append(job.get("title", ""))
        llm_results["link"].append(job.get("url", ""))
        llm_results["company_name"].append(job.get("organization", ""))
        llm_results["article_date"].append(job.get("date_posted", ""))
        llm_results["article_id"].append(job.get("id", ""))
        
        # Location mapping - handle both string and dict types
        locs = job.get("locations_derived", [])
        city, country = "", ""
        
        if locs and isinstance(locs, list) and len(locs) > 0:
            first_loc = locs[0]
            if isinstance(first_loc, dict):
                city = first_loc.get("city", "")
                country = first_loc.get("country", "")
            elif isinstance(first_loc, str):
                country = first_loc
        
        llm_results["city"].append(city)
        llm_results["country"].append(country)

        # AI-enriched fields from API
        llm_results["tags"].append(job.get("ai_key_skills", []) or [])
        llm_results["job_roles"].append(job.get("ai_taxonomies_a", []) or [])
        
        # Decision makers
        decision_makers = []
        if job.get("ai_hiring_manager_name"):
            decision_makers.append(job.get("ai_hiring_manager_name"))
        llm_results["company_decision_makers"].append(decision_makers)
        
        # Hiring reasons
        core_resp = job.get("ai_core_responsibilities")
        llm_results["hiring_reasons"].append([core_resp] if core_resp else [])

    # Merge LLM extracted data if available
    if extracted_data:
        if extracted_data.get("company_decision_makers"):
            llm_results["company_decision_makers"] = extracted_data["company_decision_makers"]
        if extracted_data.get("hiring_reasons"):
            llm_results["hiring_reasons"] = extracted_data["hiring_reasons"]
        if extracted_data.get("job_roles"):
            llm_results["job_roles"] = extracted_data["job_roles"]

    duration = asyncio.get_running_loop().time() - start_time
    logger.info(f"Active Jobs DB ingestion took {duration:.2f} seconds")
    
    return llm_results
