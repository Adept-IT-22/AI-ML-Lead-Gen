import json
import time
import httpx
import asyncio
import logging
from typing import List, Dict, Union, Any

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
        async for job in asyncio.as_completed(tasks):
            unwrapped_job = await job
            all_jobs.append(unwrapped_job)
            logger.info(json.dumps(unwrapped_job, indent=2))
        return all_jobs

    except Exception as e:
        logger.error(f"Failed to get all jobs: {str(e)}")
        
#===========GET INDIVIDUAL JOB DETAILS===============
async def get_individual_job_details(client: httpx.AsyncClient, id: int, url: str)->Dict[str, Union[str, int]]:
    logger.info("Fetching individual job details...")
    try:
        response = await client.get(f"{url}item/{id}.json?print=pretty")
        logger.info("Done fetching individual job details")
        return response.json()
        
    except Exception as e:
        logger.error(f"Couldn't fetch individual job details: {str(e)}")

#==========CONVERT LIST OF DICTS INTO DICT OF LISTS===================
def dict_of_lists(client: httpx, all_jobs: List)->Dict[str, List[Any]]:
    logger.info("Converting a list of dictionaries into a dictionary of lists")

    all_jobs_well_arranged = {
        "type": "job",
        "by": [],
        "id": [],
        "score": [],
        "text": [],
        "time": [],
        "title": [],
        "url": []
    }

    for job in all_jobs:
        for key in all_jobs_well_arranged:
            if key != "type":
                all_jobs_well_arranged[key].append(job.get(key))

    logger.info(all_jobs_well_arranged)
    return all_jobs_well_arranged

#==========FINALLY FEED TEXT (OR TITLE) INTO LLM=============

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    start_time = time.perf_counter()
    async def main():
        async with httpx.AsyncClient() as client:
            job_ids = await fetch_hackernews_jobs(url=URL, client=client)
            job_details = await get_all_job_details(client=client, ids=job_ids, url=URL)
            jobs_arranged = dict_of_lists(client=client, all_jobs=job_details)
        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")

    asyncio.run(main())