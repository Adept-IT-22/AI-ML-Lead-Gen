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

BASE_URL = "https://arc.dev"
JOBS_PAGE = "https://arc.dev/remote-jobs"

async def fetch_job_urls(client: httpx.AsyncClient) -> List[str]:
    """Fetch individual job URLs from Arc.dev remote jobs page."""
    try:
        logger.info(f"Fetching job listing page: {JOBS_PAGE}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = await client.get(JOBS_PAGE, headers=headers, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        
        # Look for patterns like /remote-jobs/j/company-slug-id
        links = re.findall(r'href=[\'"](/remote-jobs/j/[^\'"]+)[\'"]', resp.text)
        # Deduplicate and make absolute
        unique_links = list(set([BASE_URL + l if l.startswith("/") else l for l in links]))
        return unique_links
    except Exception as e:
        logger.error(f"Error fetching Arc.dev job URLs: {e}")
        return []

async def fetch_job_details(client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
    """Fetch details for a single Arc.dev job."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        # Extract ID from URL
        job_id = url.split("-")[-1]
        
        # Extract Title
        title = ""
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub('<[^<]+?>', '', title_match.group(1)).strip()
        
        # Extract Company
        company = "Unknown"
        # Try meta tag first
        company_match = re.search(r'property="og:description"\s+content="Job opportunity at (.*?) for a', html)
        if company_match:
            company = company_match.group(1).strip()
        else:
            # Try to find company name in header
            name_match = re.search(r'data-company="(.*?)"', html)
            if name_match:
                company = name_match.group(1).strip()

        # Extract Description
        description = ""
        # Arc often uses <main> or specifically classed divs
        desc_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.IGNORECASE | re.DOTALL)
        if desc_match:
            description = re.sub('<[^<]+?>', '', desc_match.group(1)).strip()
        else:
            # Fallback for structured content
            chunk = html.find('<div id="job-description"')
            if chunk != -1:
                description = re.sub('<[^<]+?>', '', html[chunk:chunk+5000]).strip()
        
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "description": description[:3000],
            "url": url,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    except Exception as e:
        logger.error(f"Error scraping Arc.dev job {url}: {e}")
        return None

async def main() -> Optional[Dict[str, Any]]:
    """Main function for Arc.dev ingestion."""
    logger.info("Starting Arc.dev hiring ingestion...")
    
    async with httpx.AsyncClient() as client:
        all_urls = await fetch_job_urls(client)
        if not all_urls:
            return copy.deepcopy(fetched_hiring_data)
        
        logger.info(f"Found {len(all_urls)} URLs on Arc.dev main search page")
        
        # Initial filter based on URL slug (contains keywords?)
        relevant_urls = []
        for url in all_urls:
            if any(role in url.lower() for role in desirable_roles):
                relevant_urls.append(url)
        
        logger.info(f"Filtered to {len(relevant_urls)} relevant URLs based on slug")
        
        # Limit processing
        targets = relevant_urls[:10]

        # CHECK IF IT EXISTS IN NORMALIZED MASTER
        
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
            logger.info(f"Submitting {len(processed_jobs)} Arc.dev jobs to AI...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"AI failed for Arc.dev: {e}")

        # Final structure
        llm_results = copy.deepcopy(fetched_hiring_data)
        llm_results["source"] = "Arc.dev"
        llm_results["type"] = "hiring"

        for job in processed_jobs:
            llm_results["title"].append(job["title"])
            llm_results["link"].append(job["url"])
            llm_results["company_name"].append(job["company"])
            llm_results["article_date"].append(job["date"])
            llm_results["article_id"].append(job["id"])
    # Merge AI
    if extracted_data:
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list) and len(value_list) == len(processed_jobs):
                llm_results[key] = value_list

        logger.info(f"Arc.dev ingestion completed. Extracted {len(llm_results['title'])} jobs.")
        return llm_results

if __name__ == "__main__":
    asyncio.run(main())
