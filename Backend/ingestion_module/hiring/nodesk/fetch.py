"""
NoDesk Jobs Fetcher
Fetches remote job listings from NoDesk sitemap.
"""
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

# Add the Backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://nodesk.co/sitemap.xml"

async def fetch_sitemap_urls(client: httpx.AsyncClient) -> List[str]:
    """Fetch job URLs from NoDesk sitemap."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await client.get(SITEMAP_URL, headers=headers, timeout=30.0)
        resp.raise_for_status()
        # Find all job URLs (format: /remote-jobs/slug/)
        locs = re.findall(r'<loc>(https?://nodesk\.co/remote-jobs/[^<]*/)</loc>', resp.text)
        return list(set(locs))
    except Exception as e:
        logger.error(f"Error fetching NoDesk sitemap: {e}")
        return []

async def fetch_job_details(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Fetch individual job page and extract data."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        # ID extraction
        job_id = url.strip("/").split("/")[-1]
        
        # Title extraction (usually in H1)
        title = ""
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub('<[^<]+?>', '', title_match.group(1)).strip()

        # Company extraction
        company = "Unknown"
        company_match = re.search(r'property="og:description"\s+content="Job opportunity at (.*?) for a', html)
        if not company_match:
             company_match = re.search(r'data-company="(.*?)"', html)
             
        if company_match:
            company = company_match.group(1).strip()

        # Description
        description = ""
        # NoDesk uses a lot of semantic HTML
        desc_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.IGNORECASE | re.DOTALL)
        if desc_match:
            description = re.sub('<[^<]+?>', '', desc_match.group(1)).strip()
            
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "description": description[:3000],
            "url": url,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    except Exception as e:
        logger.error(f"Error scraping job {url}: {e}")
        return None

async def main() -> Optional[Dict[str, Any]]:
    """Main function to fetch and process NoDesk jobs."""
    logger.info("Starting NoDesk ingestion...")
    
    async with httpx.AsyncClient() as client:
        all_urls = await fetch_sitemap_urls(client)
        if not all_urls:
             return copy.deepcopy(fetched_hiring_data)
             
        logger.info(f"Found {len(all_urls)} URLs in NoDesk sitemap")
        
        # Filter for software keywords in URL
        relevant_urls = []
        for url in all_urls:
            if any(role in url.lower() for role in desirable_roles):
                relevant_urls.append(url)
        
        logger.info(f"Filtered to {len(relevant_urls)} relevant URLs")
        
        # Take latest 10
        targets = relevant_urls[:20]

        # CHECK IF TARGETS ARE IN NORMALIZED_MASTER!!!
        
        processed_jobs = []
        for url in targets:
            job = await fetch_job_details(client, url)
            if job:
                processed_jobs.append(job)
                
        if not processed_jobs:
            return copy.deepcopy(fetched_hiring_data)

        # AI Extraction
        ids_urls_titles = {
            "ids": [job["id"] for job in processed_jobs],
            "urls": [job["url"] for job in processed_jobs],
            "titles": [f"{job['title']} at {job['company']}. Description: {job['description'][:1000]}" for job in processed_jobs]
        }
        
        extracted_data = {}
        try:
            logger.info(f"Feeding {len(processed_jobs)} NoDesk jobs to AI...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"AI failed: {e}")

        # Final structure
        llm_results = copy.deepcopy(fetched_hiring_data)
        llm_results["source"] = "NoDesk"
        llm_results["type"] = "hiring"

        # Initialize lists
        for job in processed_jobs:
            llm_results["title"].append(job["title"])
            llm_results["link"].append(job["url"])
            llm_results["company_name"].append(job["company"])
            llm_results["article_date"].append(job["date"])
            llm_results["article_id"].append(job["id"])
            for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
                llm_results[key].append([]) if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"] else llm_results[key].append("")

        # Merge AI
        if extracted_data:
             for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
                 if key in extracted_data and len(extracted_data[key]) == len(processed_jobs):
                     llm_results[key] = extracted_data[key]

        return llm_results

if __name__ == "__main__":
    asyncio.run(main())
