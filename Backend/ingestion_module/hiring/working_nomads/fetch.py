import sys
import os
import asyncio
import httpx
import re
import logging
import copy
from typing import List, Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to sys.path to allow imports from Backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

try:
    from Backend.ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
    from Backend.utils.data_structures.hiring_data_structure import fetched_hiring_data
    from Backend.utils.software_dev_keywords import software_dev_keywords
except ImportError:
    logger.error("Failed to import Backend modules. Ensure sys.path is correct.")
    # For local execution if main sys.path fails
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from Backend.ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
    from Backend.utils.data_structures.hiring_data_structure import fetched_hiring_data
    from Backend.utils.software_dev_keywords import software_dev_keywords

SITEMAP_URL = "https://www.workingnomads.com/sitemap.xml"

async def fetch_sitemap_urls(client: httpx.AsyncClient) -> List[str]:
    """Fetches the sitemap and extracts individual job post URLs."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = await client.get(SITEMAP_URL, headers=headers, timeout=30.0)
        resp.raise_for_status()
        # Simple regex to extract <loc> tags
        locs = re.findall(r'<loc>(https?://[^<]*)</loc>', resp.text)
        # Filter for job posts (containing /jobs/) and exclude the main category list
        job_links = [l for l in locs if "/jobs/" in l and l != "https://www.workingnomads.com/jobs"]
        return job_links
    except Exception as e:
        logger.error(f"Error fetching sitemap from {SITEMAP_URL}: {e}")
        return []

async def fetch_job_details(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Fetches an individual job page and extracts title, company, and description."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        # ID extraction from URL slug (usually the last numeric part or the whole slug)
        job_id = url.split("/")[-1]
        
        # Title extraction
        title = ""
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub('<[^<]+?>', '', title_match.group(1)).strip()
        else:
            og_title = re.search(r'property="og:title"\s+content="(.*?)"', html)
            if og_title:
                title = og_title.group(1)
        
        # Company extraction from Title (Pattern: "Position at Company | Working Nomads")
        company = "Unknown"
        if " at " in title:
            parts = title.split(" at ")
            title_clean = parts[0].strip()
            rest = " at ".join(parts[1:])
            if "|" in rest:
                company = rest.split("|")[0].strip()
            else:
                company = rest.strip()
            title = title_clean
        
        # Description extraction
        description = ""
        # Common containers for WN job descriptions
        desc_match = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
        if desc_match:
             description = re.sub('<[^<]+?>', '', desc_match.group(1)).strip()
        else:
            # Fallback: Capture a large chunk of content after the H1 tag and strip HTML
            h1_pos = html.find("<h1")
            if h1_pos != -1:
                chunk = html[h1_pos:h1_pos+10000]
                description = re.sub('<[^<]+?>', '', chunk).strip()
        
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "description": description[:5000], # Truncate for AI context limits
            "url": url,
            "source": "Working Nomads",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    except Exception as e:
        logger.error(f"Error fetching job details for {url}: {e}")
        return None

async def main():
    """Main execution flow for Working Nomads fetcher."""
    async with httpx.AsyncClient() as client:
        logger.info("Fetching Working Nomads sitemap...")
        all_urls = await fetch_sitemap_urls(client)
        
        if not all_urls:
            return copy.deepcopy(fetched_hiring_data)
            
        # Filter for software development jobs based on keywords in URL slug
        filtered_urls = []
        for url in all_urls:
            slug = url.split("/")[-1].lower()
            if any(re.search(rf'\b{re.escape(kw)}\b', slug) for kw in software_dev_keywords):
                filtered_urls.append(url)
        
        logger.info(f"Found {len(filtered_urls)} potentially relevant URLs.")
        
        # Take the most recent 15 relevant jobs
        targets = filtered_urls[-15:]
        
        processed_jobs = []
        for url in targets:
            logger.info(f"Scraping job: {url}")
            job = await fetch_job_details(client, url)
            if job:
                processed_jobs.append(job)
        
        if not processed_jobs:
            logger.info("No job details extracted.")
            return copy.deepcopy(fetched_hiring_data)

        # Prepare payload for AI extraction
        ids_urls_titles = {
            "ids": [job["id"] for job in processed_jobs],
            "urls": [job["url"] for job in processed_jobs],
            "titles": [f"{job['title']} at {job['company']}. Description: {job['description'][:1500]}" for job in processed_jobs]
        }
        
        extracted_data = {}
        try:
            logger.info(f"Submitting {len(processed_jobs)} jobs for AI extraction...")
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")

        # Assemble the final result using the standard hiring data structure
        llm_results = copy.deepcopy(fetched_hiring_data)
        llm_results["source"] = "working_nomads"
        llm_results["type"] = "hiring"

        for job in processed_jobs:
            llm_results["title"].append(job["title"])
            llm_results["link"].append(job["url"])
            llm_results["company_name"].append(job["company"])
            llm_results["article_date"].append(job["date"])
            llm_results["article_id"].append(job["id"])
            
            # Default empty values for fields handled by AI
            llm_results["city"].append("")
            llm_results["country"].append("")
            llm_results["company_decision_makers"].append([])
            llm_results["job_roles"].append([])
            llm_results["hiring_reasons"].append([])
            llm_results["tags"].append([])

        # Overwrite defaults with AI-extracted data if available
        if extracted_data:
            for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
                if key in extracted_data:
                    # Ensure the lists alignment matches (AI module should handle this, but let's be safe)
                    if isinstance(extracted_data[key], list) and len(extracted_data[key]) == len(processed_jobs):
                        llm_results[key] = extracted_data[key]

        logger.info(f"Working Nomads ingestion completed. Extracted {len(llm_results['title'])} jobs.")
        return llm_results

if __name__ == "__main__":
    import asyncio
    results = asyncio.run(main())
    print(f"Final results count: {len(results['title'])}")
