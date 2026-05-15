import sys
import os
import re
import logging
import httpx
import asyncio
import copy
from datetime import datetime
from typing import List, Dict, Any, Optional
import defusedxml.ElementTree as ET
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords
from utils.job_roles import desirable_roles

logger = logging.getLogger(__name__)

RSS_URL = "https://weworkremotely.com/remote-jobs.rss"

async def fetch_jobs_rss() -> str:
    """Fetch jobs from We Work Remotely RSS."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(RSS_URL, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching We Work Remotely RSS: {str(e)}")
            return ""

def parse_rss(xml_content: str) -> List[Dict[str, Any]]:
    """Parse WWR RSS content."""
    jobs = []
    try:
        root = ET.fromstring(xml_content)
        # RSS 2.0: channel -> item
        channel = root.find("channel")
        if channel is None:
            return []
            
        for item in channel.findall("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            guid = item.findtext("guid", "")
            
            jobs.append({
                "id": guid,
                "title": title,
                "url": link,
                "description": description,
                "date": pub_date,
                "company": "" # WWR RSS doesn't always have clean company tag, often in title
            })
    except Exception as e:
        logger.error(f"Failed to parse We Work Remotely XML: {str(e)}")
        
    return jobs

async def main() -> Dict[str, Any]:
    """Main function to fetch and process We Work Remotely jobs."""
    logger.info("Starting We Work Remotely hiring ingestion...")
    
    xml_content = await fetch_jobs_rss()
    if not xml_content:
        logger.warning("No content from We Work Remotely")
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = parse_rss(xml_content)
    logger.info(f"Fetched {len(raw_jobs)} jobs from We Work Remotely")

    # Filter for software/developer jobs 
    relevant_jobs = []
    for job in raw_jobs:
        # Check title and description for keywords
        text_to_check = (job.get("title", "") + " " + job.get("url", "")).lower().replace("-", " ")
        if any(re.search(rf'\b{re.escape(keyword)}\b', text_to_check) for keyword in software_dev_keywords):
             relevant_jobs.append(job)
            
    logger.info(f"Filtered out {len(raw_jobs) - len(relevant_jobs)} non-sware jobs. {len(relevant_jobs)} left")
    
    # Prepare for AI extraction
    ids_urls_titles: Dict[str, List[str]] = {
        "ids": [],
        "urls": [],
        "titles": []
    }
    
    for job in relevant_jobs:
        ids_urls_titles["ids"].append(job["id"])
        ids_urls_titles["urls"].append(job["url"])
        ids_urls_titles["titles"].append(job["title"])

    extracted_data = {}
    if relevant_jobs:
        try:
            logger.info(f"Feeding {len(relevant_jobs)} job postings to AI extraction...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"Failed to extract AI content from We Work Remotely data: {str(e)}")

    # Build result structure
    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "WeWorkRemotely"
    llm_results["type"] = "hiring"

    # Merge extracted data
    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list):
                llm_results[key] = value_list
        
        # Ensure we have all the base fields populated if AI didn't do it (AI usually does)
        # But we align lists. 
        # Note: finalize_ai_extraction returns dict of lists aligned with input.
        
        llm_results["title"] = extracted_data.get("title", ids_urls_titles["titles"])
        llm_results["link"] = extracted_data.get("article_link", ids_urls_titles["urls"])
        llm_results["article_id"] = extracted_data.get("article_id", ids_urls_titles["ids"])
        # article_date might come from extracted or original, let's trust extracted if present or fallback
        if "article_date" in extracted_data:
             llm_results["article_date"] = extracted_data["article_date"]
        else:
             llm_results["article_date"] = [job["date"] for job in relevant_jobs]

    logger.info("We Work Remotely ingestion completed")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
