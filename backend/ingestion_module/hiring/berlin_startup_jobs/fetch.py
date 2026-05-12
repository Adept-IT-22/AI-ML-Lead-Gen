import sys
import os
import re
import logging
import httpx
import asyncio
import copy
import defusedxml.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords
from utils.job_roles import desirable_roles

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RSS_URL = "https://berlinstartupjobs.com/feed/"

async def fetch_rss_content() -> str:
    """Fetch jobs from Berlin Startup Jobs RSS feed."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {RSS_URL}...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(RSS_URL, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching Berlin Startup Jobs RSS: {str(e)}")
            return ""

def parse_rss(xml_content: str) -> List[Dict[str, Any]]:
    """Parse Berlin Startup Jobs RSS content."""
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
            
            job_id = link.rstrip("/").split("/")[-1]
            
            jobs.append({
                "id": job_id,
                "title": title,
                "url": link,
                "description": description,
                "date": pub_date
            })
    except Exception as e:
        logger.error(f"Failed to parse Berlin Startup Jobs RSS XML: {str(e)}")
        
    return jobs

async def main() -> Dict[str, Any]:
    """Main function to fetch and process Berlin Startup Jobs."""
    logger.info("Starting Berlin Startup Jobs hiring ingestion...")
    
    xml_content = await fetch_rss_content()
    if not xml_content:
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = parse_rss(xml_content)
    logger.info(f"Fetched {len(raw_jobs)} jobs from Berlin Startup Jobs")

    # Filter for software development jobs
    relevant_jobs = []
    for job in raw_jobs:
        title = job.get("title")
        if title:
            title_lower = title.lower()
            if "sales" in title_lower:
                continue
            if any(role in title_lower for role in desirable_roles):
                relevant_jobs.append(job)
            
    logger.info(f"Filtered to {len(relevant_jobs)} relevant software development jobs")

    targets = relevant_jobs[:10]

    # CHECK IF TARGETS IN NORMALIZED_MASTER
    
    if not targets:
        return copy.deepcopy(fetched_hiring_data)

    ids_urls_titles = {
        "ids": [job["id"] for job in targets],
        "urls": [job["url"] for job in targets],
        "titles": [f"{job['title']}. Details: {job['description'][:1500]}" for job in targets]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} Berlin Startup Jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed for Berlin Startup Jobs: {e}")

    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Berlin Startup Jobs"
    llm_results["type"] = "hiring"

    for job in targets:
        llm_results["title"].append(job["title"].split("//")[0])
        llm_results["link"].append(job["url"])
        llm_results["article_date"].append(job["date"])
        llm_results["article_id"].append(job["id"])

    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list) and len(value_list) == len(targets):
                llm_results[key] = value_list

    logger.info(f"Berlin Startup Jobs ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
