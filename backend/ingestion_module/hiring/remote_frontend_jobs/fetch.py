import sys
import os
import re
import logging
import httpx
import asyncio
import copy
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SITEMAP_URL = "https://www.remotefrontendjobs.com/sitemap.xml"

async def fetch_url_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch text content from a URL."""
    try:
        response = await client.get(url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return ""

async def fetch_job_details(client: httpx.AsyncClient, job: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch job page to get title/description if possible, or infer from URL."""
    # Infer title from slug first as backup
    slug = job["url"].rstrip("/").split("/")[-1]
    inferred_title = " ".join(word.capitalize() for word in slug.split("-") if not re.match(r'^[a-z0-9]+$', word)) # Attempt to skip id parts
    
    html = await fetch_url_text(client, job["url"])
    if html:
        # Simple regex extraction for Title to avoid heavy parsing libs
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title_match:
            job["title"] = title_match.group(1).replace(" | Remote Frontend Jobs", "").strip()
        else:
            job["title"] = inferred_title
            
        # Extract meta description
        desc_match = re.search(r'<meta name="description" content="(.*?)"', html, re.IGNORECASE)
        if desc_match:
            job["description"] = desc_match.group(1)
        else:
            # Fallback: take first 1000 chars of body
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
            job["description"] = body_match.group(1)[:2000] if body_match else ""
    else:
        job["title"] = inferred_title
        job["description"] = "Remote role."

    return job

async def main() -> Dict[str, Any]:
    """Main function to fetch and process Remote Frontend Jobs."""
    logger.info("Starting Remote Frontend Jobs ingestion...")
    
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        sitemap_xml = await fetch_url_text(client, SITEMAP_URL)
        if not sitemap_xml:
             return copy.deepcopy(fetched_hiring_data)
        
        # Parse Sitemap
        try:
            root = ET.fromstring(sitemap_xml)
            # Handle namespace
            ns = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            for url_tag in root.findall('sitemap:url', ns):
                loc_elem = url_tag.find('sitemap:loc', ns)
                if loc_elem is None or not loc_elem.text:
                    continue
                loc = loc_elem.text

                lastmod_elem = url_tag.find('sitemap:lastmod', ns)
                lastmod = lastmod_elem.text if lastmod_elem is not None and lastmod_elem.text else ""
                
                # Filter out static pages
                if loc.strip('/').endswith("remote-frontend-jobs") or loc == "https://www.remotefrontendjobs.com":
                    continue
                if loc.endswith("-jobs"): # Category pages
                    continue
                    
                urls.append({"url": loc, "lastmod": lastmod})
                
            # Sort by lastmod descending
            urls.sort(key=lambda x: x["lastmod"], reverse=True)
            
            logger.info(f"Found {len(urls)} job URLs in sitemap")
            
            # Take top 10 latest
            targets = urls[:10]

            # CHECK IF IN NORMALIZED_MASTER 

            logger.info("TARGETS\n%r", targets[0])
            
            # Fetch details in parallel
            tasks = [fetch_job_details(client, job) for job in targets]
            detailed_jobs = await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Failed to parse sitemap: {e}")
            return copy.deepcopy(fetched_hiring_data)

    ids_urls_titles = {
        "ids": [job["url"].split("/")[-1] for job in detailed_jobs],
        "urls": [job["url"] for job in detailed_jobs],
        "titles": [f"{job['title']}. Details: {job.get('description', '')[:1000]}" for job in detailed_jobs]
    }

    extracted_data = {}
    try:
        logger.info(f"Feeding {len(detailed_jobs)} Remote Frontend Jobs to AI extraction...")
        extracted_data = await finalize_ai_extraction(ids_urls_titles)
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")

    llm_results = copy.deepcopy(fetched_hiring_data)
    llm_results["source"] = "Remote Frontend Jobs"
    llm_results["type"] = "hiring"

    for job in detailed_jobs:
        llm_results["title"].append(job["title"])
        llm_results["link"].append(job["url"])
        llm_results["article_date"].append(job["lastmod"])
        llm_results["article_id"].append(job["url"].split("/")[-1])
        
        llm_results["company_name"].append("")
        for key, value_list in extracted_data.items():
            if key in llm_results and isinstance(value_list, list) and len(value_list) == len(targets):
                 llm_results[key] = value_list

    logger.info(f"Remote Frontend Jobs ingestion completed. Extracted {len(llm_results['title'])} jobs.")
    return llm_results

if __name__ == "__main__":
    asyncio.run(main())
