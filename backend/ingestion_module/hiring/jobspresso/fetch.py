"""
Jobspresso Jobs Fetcher
Fetches remote job listings from Jobspresso RSS feed.
"""
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

SITEMAP_URL = "https://jobspresso.co/job_listing-sitemap4.xml"

async def fetch_sitemap_urls(client: httpx.AsyncClient) -> List[str]:
    """Fetch job URLs from Jobspresso sitemap."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await client.get(SITEMAP_URL, headers=headers, timeout=30.0)
        resp.raise_for_status()
        # Find all job URLs
        locs = re.findall(r'<loc>(https?://jobspresso\.co/job/[^<]*)</loc>', resp.text)
        return list(set(locs))
    except Exception as e:
        logger.error(f"Error fetching Jobspresso sitemap: {e}")
        return []

async def fetch_job_details(client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
    """Fetch individual job page and extract data."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        # ID extraction
        job_id = url.strip("/").split("/")[-1]
        
        # Title extraction
        title = ""
        title_match = re.search(r'<h1[^>]*class="[^"]*job_title[^"]*"[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
            
        if title_match:
            title = re.sub('<[^<]+?>', '', title_match.group(1)).strip()

        # Company extraction
        company = "Unknown"
        # 1. Try job-company class
        company_match = re.search(r'<li[^>]*class="job-company"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        if not company_match:
             # 2. Try JSON-LD
             company_match = re.search(r'"hiringOrganization":\s*{[^}]*"name":\s*"(.*?)"', html, re.IGNORECASE | re.DOTALL)
        
        if company_match:
            company = re.sub('<[^<]+?>', '', company_match.group(1)).strip()

        # Location extraction
        location = ""
        loc_match = re.search(r'<li[^>]*class="location"[^>]*>(.*?)</li>', html, re.IGNORECASE | re.DOTALL)
        if loc_match:
            location = re.sub('<[^<]+?>', '', loc_match.group(1)).strip()

        # Date extraction
        posted_date = ""
        date_match = re.search(r'<li[^>]*class="date-posted"[^>]*>.*?<date>(.*?)</date>', html, re.IGNORECASE | re.DOTALL)
        if date_match:
            posted_date = date_match.group(1).replace("Posted ", "").strip()

        # Description
        description = ""
        desc_match = re.search(r'<div[^>]*class="[^"]*job_description[^"]*"[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
        if desc_match:
            description = re.sub('<[^<]+?>', '', desc_match.group(1)).strip()
            
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": description[:3000],
            "url": url,
            "date": posted_date
        }
    except Exception as e:
        logger.error(f"Error scraping job {url}: {e}")
        return None

async def main() -> Dict[str, Any]:
    """Main function to fetch and process Jobspresso jobs."""
    logger.info("Starting Jobspresso ingestion (Sitemap Scrape)...")
    
    async with httpx.AsyncClient() as client:
        all_urls = await fetch_sitemap_urls(client)
        if not all_urls:
             return copy.deepcopy(fetched_hiring_data)
             
        logger.info(f"Found {len(all_urls)} URLs in Jobspresso sitemap")
        
        # Filter for software keywords in URL
        relevant_urls = []
        for url in all_urls:
            #if any(re.search(rf'\b{re.escape(kw)}\b', url.lower().replace("-", " ")) for kw in software_dev_keywords):
                #relevant_urls.append(url)
            if any(role in url.lower() for role in desirable_roles):
                relevant_urls.append(url)
        
        logger.info(f"Filtered to {len(relevant_urls)} relevant URLs")
        
        # Take latest 10
        targets = relevant_urls[:10]

        # CHECK IF TARGETS IN NORMALIZED_MASTER!!!
        
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
            logger.info(f"Feeding {len(processed_jobs)} jobs to AI...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"AI failed: {e}")

        # Final structure
        llm_results = copy.deepcopy(fetched_hiring_data)
        llm_results["source"] = "Jobspresso"
        llm_results["type"] = "hiring"

        # Initialize lists
        for job in processed_jobs:
            llm_results["title"].append(job["title"])
            llm_results["link"].append(job["url"])
            llm_results["company_name"].append(job["company"])
            llm_results["article_date"].append(job["date"] or datetime.now().strftime("%Y-%m-%d"))
            llm_results["article_id"].append(job["id"])

        # Merge AI
        if extracted_data:
            for key, value_list in extracted_data.items():
                if key in llm_results and isinstance(value_list, list) and len(value_list) == len(processed_jobs):
                    llm_results[key] = value_list

        
        return llm_results

if __name__ == "__main__":
    import pprint
    import yappi
    from profiling_module.profiling import handle_profiling
    
    yappi.set_clock_type("wall") # Use wall time for asyncio
    yappi.start()
    
    results = asyncio.run(main())
    
    yappi.stop()
    asyncio.run(handle_profiling()) # handle_profiling is async
    
    pprint.pprint(results)
