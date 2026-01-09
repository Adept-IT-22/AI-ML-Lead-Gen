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

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RSS_URL = "https://devitjobs.nl/jobs/remote/rss"

async def fetch_rss_content() -> str:
    """Fetch jobs from DevIT Jobs NL RSS feed."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching jobs from {RSS_URL}...")
            headers = {"User-Agent": "Mozilla/5.0"}
            response = await client.get(RSS_URL, headers=headers, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching DevIT Jobs NL RSS: {str(e)}")
            return ""

def parse_rss(xml_content: str) -> List[Dict[str, Any]]:
    """Parse DevIT Jobs NL RSS content."""
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
        logger.error(f"Failed to parse DevIT Jobs NL RSS XML: {str(e)}")
    return jobs

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process DevIT Jobs NL."""
    logger.info("Starting DevIT Jobs NL hiring ingestion...")
    
    xml_content = await fetch_rss_content()
    if not xml_content:
        return copy.deepcopy(fetched_hiring_data)

    raw_jobs = parse_rss(xml_content)
    logger.info(f"Fetched {len(raw_jobs)} jobs from DevIT Jobs NL")

    relevant_jobs = []
    for job in raw_jobs:
        text_to_check = (job.get("title", "") + " " + job.get("description", "")).lower().replace("-", " ")
        if any(re.search(rf'\b{re.escape(keyword)}\b', text_to_check) for keyword in software_dev_keywords):
            relevant_jobs.append(job)
            
    logger.info(f"Filtered to {len(relevant_jobs)} relevant software development jobs")

    targets = relevant_jobs[:10]
    if not targets:
        return copy.deepcopy(fetched_hiring_data)

    ids_urls_titles = {
        "ids": [job["id"] for job in targets],
        "urls": [job["url"] for job in targets],
        "titles": [f"{job['title']}. Details: {job['description'][:1500]}" for job in targets]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(targets)} DevIT Jobs NL to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed for DevIT Jobs NL: {e}")

    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "DevIT Jobs NL"
    llm_results["type"] = "hiring"

    for job in targets:
        llm_results["title"].append(job["title"])
        llm_results["link"].append(job["url"])
        llm_results["article_date"].append(job["date"])
        llm_results["article_id"].append(job["id"])
        llm_results["company_name"].append("")
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
            if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"]:
                llm_results[key].append([])
            else:
                llm_results[key].append("")

    if extracted_data:
        for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "company_name", "city", "country"]:
            if key in extracted_data and len(extracted_data[key]) == len(targets):
                llm_results[key] = extracted_data[key]

    logger.info(f"DevIT Jobs NL ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
