import sys
import os
import re
import logging
import httpx
import asyncio
import copy
import xml.etree.ElementTree as ET
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

RSS_URL = "https://djinni.co/jobs/rss/"

async def fetch_rss_content() -> str:
    """Fetch jobs from Djinni RSS feed."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {RSS_URL}...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await client.get(RSS_URL, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching Djinni RSS: {str(e)}")
            return ""

def parse_rss(xml_content: str) -> List[Dict[str, Any]]:
    """Parse Djinni RSS content."""
    jobs = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        if channel is None:
            return []
            
        for item in channel.findall("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            
            # Simple ID from link
            # Example: https://djinni.co/jobs/12345/
            job_id = link.rstrip("/").split("/")[-1]
            
            jobs.append({
                "id": job_id,
                "title": title,
                "url": link,
                "description": description,
                "date": pub_date
            })
    except Exception as e:
        logger.error(f"Failed to parse Djinni RSS XML: {str(e)}")
        
    return jobs

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process Djinni jobs."""
    logger.info("Starting Djinni hiring ingestion...")
    
    xml_content = await fetch_rss_content()
    if not xml_content:
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = parse_rss(xml_content)
    logger.info(f"Fetched {len(raw_jobs)} jobs from Djinni")

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

    # CHECK IF TARGETS IN NORMALIZED_MASTER

    # Prepare for AI extraction
    ids_urls_titles = {
        "ids": [job["id"] for job in targets],
        "urls": [job["url"] for job in targets],
        "titles": [f"{job['title']}. Content: {job['description'][:1500]}" for job in targets]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} Djinni jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed for Djinni: {e}")

    # Final result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Djinni"
    llm_results["type"] = "hiring"

    for job in targets:
        llm_results["title"].append(job["title"])
        llm_results["link"].append(job["url"])
        llm_results["article_date"].append(job["date"])
        llm_results["article_id"].append(job["id"])
        
        # Placeholders
        llm_results["company_name"].append("") # AI should fill this
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"]:
                llm_results[key].append([])
            else:
                llm_results[key].append("")

    # Merge AI
    if extracted_data:
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "company_name", "city", "country"]:
            if key in extracted_data and len(extracted_data[key]) == len(targets):
                llm_results[key] = extracted_data[key]

    logger.info(f"Djinni ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
