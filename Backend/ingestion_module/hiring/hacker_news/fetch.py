"""
Hacker News "Who is Hiring" Thread Parser
Fetches monthly "Who is Hiring" threads from RSS feed and extracts individual job postings from comments.
Similar to funding modules, this parses structured data and feeds it to AI extraction.
"""

import copy
import re
import time
import httpx
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from lxml import etree
from email.utils import parsedate_to_datetime
from services.request_headers import get_header
from utils.data_structures.hiring_data_structure import fetched_hiring_data as hiring_fetched_data

logger = logging.getLogger(__name__)

# URLs
RSS_URL = "https://news.ycombinator.com/rss"
HN_API_URL = "https://hacker-news.firebaseio.com/v0/"

# Tech keywords for filtering
TECH_KEYWORDS = [
    "software", "engineer", "developer", "programmer", "tech", "technology",
    "backend", "frontend", "full stack", "fullstack", "devops", "sre",
    "data", "analyst", "scientist", "architect", "lead", "senior",
    "python", "javascript", "java", "react", "node", "typescript",
    "cloud", "aws", "azure", "gcp", "kubernetes", "docker",
    "api", "microservices", "distributed systems", "scalable",
    "startup", "saas", "platform", "infrastructure", "security"
]

# Semaphore for rate limiting
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

#Lets use last 30 days instead of 1last 2 month
def is_within_last_month(pub_date: Optional[str]) -> bool:
    """
    Check if a publication date is within the last month.
    RSS feeds typically use RFC 2822 format (e.g., "Mon, 05 Nov 2025 12:01:00 +0000").
    """
    if not pub_date:
        return False  # Exclude if no date available (fail closed)
    
    try:
        # Parse RFC 2822 date format (common in RSS feeds)
        parsed_date = parsedate_to_datetime(pub_date)
        
        if not parsed_date:
            return False
        
        # Make sure date is timezone-aware
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        
        # Compare with timezone-aware current time (last 30 days = 1 month)
        one_month_ago = datetime.now(parsed_date.tzinfo) - timedelta(days=30)
        return parsed_date >= one_month_ago
        
    except Exception as e:
        logger.debug(f"Error parsing date '{pub_date}': {str(e)}")
        return False  # Exclude if can't parse (fail closed)


async def fetch_who_is_hiring_threads(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """
    Fetch "Who is Hiring" threads from Hacker News API.
    Uses the API to get submissions from the 'whoishiring' user.
    Returns list of thread metadata.
    """
    logger.info("Fetching 'Who is Hiring' threads from Hacker News API...")
    try:
        # First, get the user ID for 'whoishiring'
        user_response = await client.get(f"{HN_API_URL}user/whoishiring.json", timeout=30.0)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        if not user_data or 'submitted' not in user_data:
            logger.warning("Could not find submissions for 'whoishiring' user")
            return []
        
        # Get submitted item IDs (limit to first 100 to check recent ones)
        submitted_ids = user_data['submitted'][:100]
        logger.info(f"Found {len(submitted_ids)} submissions from 'whoishiring' user")
        
        threads = []
        
        # Fetch each submission to check if it's a "Who is Hiring" thread
        async def fetch_submission(item_id: int):
            async with semaphore:
                try:
                    response = await client.get(f"{HN_API_URL}item/{item_id}.json", timeout=30.0)
                    response.raise_for_status()
                    item_data = response.json()
                    
                    if not item_data or item_data.get('type') != 'story':
                        return None
                    
                    title = item_data.get('title', '').strip()
                    time_stamp = item_data.get('time')
                    
                    # Filter for "Who is Hiring" threads
                    if 'who is hiring' in title.lower() or 'who\'s hiring' in title.lower():
                        # Convert Unix timestamp to RFC 2822 date format
                        if time_stamp:
                            from datetime import datetime, timezone
                            pub_date = datetime.fromtimestamp(time_stamp, tz=timezone.utc)
                            pub_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S %z")
                            
                            # Filter by date: only include threads from last month
                            if not is_within_last_month(pub_date_str):
                                logger.debug(f"Skipping thread '{title}' - older than 1 month")
                                return None
                            
                            link = f"https://news.ycombinator.com/item?id={item_id}"
                            
                            thread_info = {
                                'id': str(item_id),
                                'title': title,
                                'link': link,
                                'pub_date': pub_date_str
                            }
                            logger.info(f"Found 'Who is Hiring' thread: {title} (ID: {item_id})")
                            return thread_info
                    
                    return None
                except Exception as e:
                    logger.debug(f"Error fetching submission {item_id}: {str(e)}")
                    return None
        
        # Fetch all submissions concurrently
        tasks = [fetch_submission(item_id) for item_id in submitted_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        threads = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        logger.info(f"Found {len(threads)} 'Who is Hiring' threads from last month")
        return threads
        
    except Exception as e:
        logger.error(f"Error fetching 'Who is Hiring' threads: {str(e)}")
        return []


async def fetch_thread_comments(client: httpx.AsyncClient, thread_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all comments from a Hacker News thread using the API.
    Returns list of top-level comments (job postings).
    """
    logger.info(f"Fetching comments for thread {thread_id}...")
    try:
        # Fetch the thread item
        response = await client.get(f"{HN_API_URL}item/{thread_id}.json", timeout=30.0)
        response.raise_for_status()
        thread_data = response.json()
        
        if not thread_data or 'kids' not in thread_data:
            logger.warning(f"No comments found for thread {thread_id}")
            return []
        
        # Fetch all top-level comments (kids)
        comment_ids = thread_data['kids'][:500]  # Limit to first 500 comments
        logger.info(f"Fetching {len(comment_ids)} comments from thread {thread_id}...")
        
        async def fetch_comment(comment_id: int):
            async with semaphore:
                try:
                    response = await client.get(f"{HN_API_URL}item/{comment_id}.json", timeout=30.0)
                    response.raise_for_status()
                    comment_data = response.json()
                    
                    # Only return top-level comments (not replies)
                    if comment_data and comment_data.get('type') == 'comment':
                        return comment_data
                    return None
                except Exception as e:
                    logger.debug(f"Error fetching comment {comment_id}: {str(e)}")
                    return None
        
        # Fetch all comments concurrently
        tasks = [fetch_comment(cid) for cid in comment_ids]
        comments = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        valid_comments = [
            c for c in comments 
            if c is not None and not isinstance(c, Exception)
        ]
        
        logger.info(f"Fetched {len(valid_comments)} valid comments from thread {thread_id}")
        return valid_comments
        
    except Exception as e:
        logger.error(f"Error fetching thread comments: {str(e)}")
        return []


def is_tech_related_job(text: str) -> bool:
    """
    Check if a job posting is tech-related.
    """
    if not text:
        return False
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TECH_KEYWORDS)


def extract_job_postings(comments: List[Dict[str, Any]], thread_id: str, thread_link: str) -> Dict[str, List[Any]]:
    """
    Extract and filter job postings from comments.
    Returns structured data for AI extraction.
    """
    logger.info(f"Extracting job postings from {len(comments)} comments...")
    
    job_postings = {
        "ids": [],
        "urls": [],
        "titles": []
    }
    
    for comment in comments:
        text = comment.get('text', '')
        comment_id = comment.get('id')
        
        if not text or not comment_id:
            continue
        
        # Filter for tech-related jobs
        if is_tech_related_job(text):
            # Create a title from the first line or first 100 chars
            lines = text.split('\n')
            title = lines[0].strip()[:100] if lines else text[:100]
            
            # Create a link to the comment
            comment_link = f"https://news.ycombinator.com/item?id={comment_id}"
            
            job_postings["ids"].append(str(comment_id))
            job_postings["urls"].append(comment_link)
            job_postings["titles"].append(title)
            
            logger.debug(f"Found tech-related job posting: {title[:50]}...")
    
    logger.info(f"Extracted {len(job_postings['ids'])} tech-related job postings")
    return job_postings


async def main():
    """
    Main function to fetch "Who is Hiring" data from Hacker News.
    Similar to funding modules, this follows the same pattern:
    1. Fetch data from source (RSS feed)
    2. Parse and filter for relevant content (tech-related jobs)
    3. Feed to AI extraction module
    4. Return structured data
    """
    start_time = time.perf_counter()
    logger.info("Starting Hacker News 'Who is Hiring' data fetch...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Step 1: Fetch "Who is Hiring" threads from Hacker News API
            threads = await fetch_who_is_hiring_threads(client)
            
            if not threads:
                logger.warning("No 'Who is Hiring' threads found")
                return {}
            
            # Step 2: Process all threads from last month
            all_job_postings = {
                "ids": [],
                "urls": [],
                "titles": []
            }
            
            for thread in threads:
                thread_id = thread['id']
                thread_link = thread['link']
                
                logger.info(f"Processing thread: {thread['title']}")
                
                # Step 3: Fetch all comments from the thread
                comments = await fetch_thread_comments(client, thread_id)
                
                if not comments:
                    logger.warning(f"No comments found in thread {thread_id}")
                    continue
                
                # Step 4: Extract job postings from comments
                thread_job_postings = extract_job_postings(comments, thread_id, thread_link)
                
                # Combine with all job postings
                all_job_postings["ids"].extend(thread_job_postings["ids"])
                all_job_postings["urls"].extend(thread_job_postings["urls"])
                all_job_postings["titles"].extend(thread_job_postings["titles"])
            
            # Use combined job postings from all threads
            job_postings = all_job_postings
            
            if not job_postings["ids"]:
                logger.warning("No tech-related job postings found")
                return {}
            
            # Step 5: Feed to AI extraction module
            logger.info(f"Feeding {len(job_postings['ids'])} job postings to AI extraction...")
            try:
                # Lazy import to avoid loading Gemini model during module import
                from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
                extracted_data = await finalize_ai_extraction(job_postings)
            except Exception as e:
                logger.error(f"Failed to extract AI content from HackerNews data: {str(e)}")
                extracted_data = {}
            
            # Step 6: Format results (similar to funding modules)
            llm_results = None
            if extracted_data:
                llm_results = copy.deepcopy(hiring_fetched_data)
                
                for key, value in extracted_data.items():
                    if key in llm_results and isinstance(llm_results[key], list):
                        llm_results[key].extend(value)
                    elif key in llm_results:
                        llm_results[key] = value
                
                # Set source and link
                llm_results["source"] = "HackerNews"
                llm_results["link"] = job_postings.get("urls", [])
            else:
                logger.warning("AI extraction for HackerNews 'Who is Hiring' returned no data")
            
            duration = time.perf_counter() - start_time
            
            # Print comprehensive summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("EXTRACTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total time: {duration:.2f} seconds ({duration/60:.1f} minutes)")
            logger.info(f"Input job postings: {len(job_postings.get('ids', []))}")
            
            if llm_results:
                num_results = len(llm_results.get("article_id", []))
                logger.info("")
                logger.info(f"✓ Successfully extracted: {num_results} job postings")
                
                if num_results > 0:
                    # Get unique counts
                    companies = [c for c in llm_results.get('company_name', []) if c]
                    unique_companies = len(set(companies)) if companies else 0
                    
                    job_roles = []
                    for roles in llm_results.get('job_roles', []):
                        if isinstance(roles, list):
                            job_roles.extend(roles)
                        elif roles:
                            job_roles.append(roles)
                    unique_roles = len(set(job_roles)) if job_roles else 0
                    
                    cities = [c for c in llm_results.get('city', []) if c]
                    unique_cities = len(set(cities)) if cities else 0
                    
                    countries = [c for c in llm_results.get('country', []) if c]
                    unique_countries = len(set(countries)) if countries else 0
                    
                    logger.info("")
                    logger.info("Extracted Data Breakdown:")
                    logger.info(f"  • Unique Companies: {unique_companies}")
                    logger.info(f"  • Unique Job Roles: {unique_roles}")
                    logger.info(f"  • Unique Cities: {unique_cities}")
                    logger.info(f"  • Unique Countries: {unique_countries}")
                    
                    # Show sample results
                    logger.info("")
                    logger.info("Sample Results (first 5):")
                    for i in range(min(5, num_results)):
                        article_id = llm_results.get("article_id", [])[i] if i < len(llm_results.get("article_id", [])) else "N/A"
                        company = companies[i] if i < len(companies) else "N/A"
                        role = job_roles[i] if i < len(job_roles) else "N/A"
                        city = cities[i] if i < len(cities) else "N/A"
                        logger.info(f"  {i+1}. ID: {article_id} | Company: {company} | Role: {role} | City: {city}")
            else:
                logger.warning("")
                logger.warning("✗ No results extracted")
            
            logger.info("")
            logger.info("=" * 80)
            
            return llm_results if llm_results else {}
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        return {}

if __name__ == "__main__":
    asyncio.run(main())