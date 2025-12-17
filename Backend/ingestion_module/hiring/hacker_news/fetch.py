import copy
import json
import time
import httpx
import asyncio
import logging
import aiofiles
from typing import List, Dict, Union, Any
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import fetched_hiring_data as hiring_fetched_data
from utils.software_dev_keywords import software_dev_keywords

logger = logging.getLogger()

#=============HACKERNEWS URL===========
URL = "https://hacker-news.firebaseio.com/v0/"

"""
The function below fetches jobs from hackernews.They
come back as IDs which we'll have to send another request 
to get the data for.
"""
async def fetch_hackernews_jobs(client: httpx.AsyncClient, url: str)->List:
    logger.info("Fetching jobs form hackernews...")
    try:
        response = await client.get(f"{url}jobstories.json")
        
        logger.info("Done fetching jobs form hackernews")
        return response.json()

    except Exception as e:
        logger.error(f"Couldn't fetch jobs from hackernews: {str(e)}")

#==============GET ALL JOB DETAILS==================
async def get_all_job_details(client: httpx.AsyncClient, ids: List, url: str)->List[Dict]:
    logger.info("Getting all jobs...")
    try:
        tasks = [get_individual_job_details(client, id, url) for id in ids]
        all_jobs = []
        for job in asyncio.as_completed(tasks):
            unwrapped_job = await job
            all_jobs.append(unwrapped_job)
        logger.info("Done getting all jobs' details")
        return all_jobs

    except Exception as e:
        logger.error(f"Failed to get all jobs: {str(e)}")
        
#===========GET INDIVIDUAL JOB DETAILS===============
async def get_individual_job_details(client: httpx.AsyncClient, id: int, url: str)->Dict[str, Union[str, int]]:
    logger.info("Fetching individual job details...")
    try:
        response = await client.get(f"{url}item/{id}.json?print=pretty")
        logger.info("Done fetching individual job details")
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Couldn't fetch individual job details: {str(e)}")

#==========CONVERT LIST OF DICTS INTO DICT OF LISTS===================
def dict_of_lists(all_jobs: List[Dict])->Dict[str, List[Any]]:
    logger.info("Converting a list of dictionaries into a dictionary of lists")

    all_jobs_well_arranged = {
        "type": "hiring",
        "by": [],
        "id": [],
        "score": [],
        "text": [],
        "time": [],
        "title": [],
        "url": []
    }

    for job in all_jobs:
        if any(keyword in job.get("url", "").lower() or keyword in job.get("title", "").lower() for keyword in software_dev_keywords):
            for key in all_jobs_well_arranged:
                if key != "type":
                    value = job.get(key)
                    all_jobs_well_arranged[key].append("" if value is None else value)

    return all_jobs_well_arranged

async def main():
    start_time = time.perf_counter()
    async with httpx.AsyncClient() as client:
        job_ids = await fetch_hackernews_jobs(url=URL, client=client)
        job_details = await get_all_job_details(client=client, ids=job_ids, url=URL)
        jobs_arranged_and_filtered = dict_of_lists(all_jobs=job_details)

        #extract id, url and title only from all arranged jobs
        ids_urls_titles = {}
        ids_urls_titles["ids"] = jobs_arranged_and_filtered.get("id", "")
        ids_urls_titles["urls"] = jobs_arranged_and_filtered.get("url", "")
        ids_urls_titles["titles"] = jobs_arranged_and_filtered.get("title", "")
        
        #feed to llm
        try:
            extracted_data = await finalize_ai_extraction(ids_urls_titles)
        except Exception as e:
            logger.error(f"Failed to extract AI content from HackerNews data: {str(e)}")
            extracted_data = {}

    #put extracted data to llm_results
    llm_results = None
    if extracted_data:
        llm_results = copy.deepcopy(hiring_fetched_data)
        for key, value in extracted_data.items():
            if key in llm_results and isinstance(llm_results[key], list):
                llm_results[key].extend(value)
            elif key in llm_results:
                llm_results[key] = value

        #"by" in jobs_arranged_and_filtered = "company_decision_makers" in llm_results
        llm_results["company_decision_makers"].extend(jobs_arranged_and_filtered["by"])
        llm_results["source"] = "HackerNews"
        llm_results["link"] = jobs_arranged_and_filtered.get("url", [])

        for by_value in jobs_arranged_and_filtered["by"]:
            llm_results["company_decision_makers"].append([by_value])

    else:
        logger.warning("AI extraction for HackerNews returned no data. No logging will happen")

    duration = time.perf_counter() - start_time
    logger.info(f"This task took {duration:.2f} seconds")

    return llm_results

if __name__ == "__main__":
    asyncio.run(main())