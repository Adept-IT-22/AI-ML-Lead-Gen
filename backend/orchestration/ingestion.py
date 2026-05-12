import logging
import asyncio
from typing import Dict, Any, List
from helpers.helpers import wrap
from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.funding.cbinsights.fetch import main as cbinsights_main
from ingestion_module.funding.sifted_eu.fetch import main as sifted_eu_main
from ingestion_module.funding.siliconangle.fetch import main as siliconangle_main
from ingestion_module.funding.techfundingnews.fetch import main as techfundingnews_main
from ingestion_module.funding.ventureburn.fetch import main as ventureburn_main
from ingestion_module.funding.venture_beat.fetch import main as venture_beat_main
from ingestion_module.funding.betakit.fetch import main as betakit_main
from ingestion_module.funding.startup_hub.fetch import main as startup_hub_main
from ingestion_module.funding.eu_startups.fetch import main as eu_startups_main
from ingestion_module.funding.thenextweb.fetch import main as thenextweb_main
from ingestion_module.funding.vestbee.fetch import main as vestbee_main
from ingestion_module.funding.pr_news_wire.fetch import main as pr_news_wire_main
from ingestion_module.funding.geekwire.fetch import main as geekwire_main
from ingestion_module.funding.eu_entrepreneur.fetch import main as eu_entrepreneur_main
from ingestion_module.funding.hyper_latam.fetch import main as hyper_latam_main
from ingestion_module.funding.inc42.fetch import main as inc42_main
from ingestion_module.funding.smart_company.fetch import main as smart_company_main
from ingestion_module.funding.silicon_republic.fetch import main as silicon_republic_main
from ingestion_module.funding.american_bazaar_online.fetch import main as american_bazaar_online_main
from ingestion_module.funding.startup_daily_net.fetch import main as startup_daily_net_main
from ingestion_module.hiring.active_jobs_db.fetch import main as active_jobs_db_main
from ingestion_module.hiring.jobspresso.fetch import main as jobspresso_main
from ingestion_module.hiring.arbeitnow.fetch import main as arbeitnow_main
from ingestion_module.hiring.crunchboard.fetch import main as crunchboard_main
from ingestion_module.hiring.python_org.fetch import main as python_org_main
from ingestion_module.hiring.arc_dev.fetch import main as arc_dev_main
from ingestion_module.hiring.remoteok.fetch import main as remoteok_main
from ingestion_module.hiring.remotive.fetch import main as remotive_main
from ingestion_module.hiring.we_work_remotely.fetch import main as we_work_remotely_main
from ingestion_module.hiring.working_nomads.fetch import main as working_nomads_main
from ingestion_module.hiring.nodesk.fetch import main as nodesk_main
from ingestion_module.hiring.himalayas.fetch import main as himalayas_main
from ingestion_module.hiring.jobicy.fetch import main as jobicy_main
from ingestion_module.hiring.four_day_week.fetch import main as four_day_week_main
from ingestion_module.hiring.djinni.fetch import main as djinni_main
from ingestion_module.hiring.berlin_startup_jobs.fetch import main as berlin_startup_jobs_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.hiring.remote_frontend_jobs.fetch import main as remote_frontend_jobs_main


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def run_ingestion_modules()->Dict:
    #Each coroutine and it's name
    coroutines: list[tuple[str, Any]] = [
        #("finsmes", finsmes_main()),
        # ... (rest of the commented out lines)
    ]

    #A list of wrap coroutine objects to be run
    tasks = [wrap(name, coroutine) for name, coroutine in coroutines]

    results = {} #Will store info about each coroutines status
    
    #Process the coroutines as they complete
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
    for task_result in completed_tasks:
        if isinstance(task_result, (Exception, BaseException)):
            logger.error(f"A task failed catastrophically: {task_result}")
            continue
        
        # We expect a tuple (name, result) from wrap
        if not isinstance(task_result, tuple) or len(task_result) != 2:
            logger.error(f"Unexpected task result format: {task_result}")
            continue

        name, result = task_result
        if isinstance(result, Exception):
            logger.error(f"Task '{name}' failed: {result}")
        else:
            logger.info(f"Task '{name}' completed successfully")

        #Add each coroutine's name and result to the results dictionary
        results[name] = result

    logger.info("All ingestion tasks have been completed")

    logger.info(f"\n============FINAL SUMMARY============")
    for name, result in results.items():
        status = "SUCCESS ✅" if not isinstance(result, Exception) else "FAILED ❌"
        logger.info(f"{name}: {status}")

    return results

#Put results in queue.
"""
Results below will be a dictionary of dictionaries i.e.
{
    results = {
        "finmes": {
            "type": "funding",
            "source": "finsmes",
            etc.
        }
    }
}
"""

#Populate queue and return it
async def main(ingestion_to_normalization_queue: asyncio.Queue)->asyncio.Queue:
    results = await run_ingestion_modules()

    logger.info("Adding ingestion module results to queue 🚂")

    #Add {"finsmes": {}, "tech_eu": {}, "eventbrite": {}}
    for name, result in results.items():
        if not isinstance(result, Exception) and isinstance(result, dict) and result.get("type"):
            #Put name and result in queue for easier debugging
            await ingestion_to_normalization_queue.put((name, result))
            logger.info(f"The ingestion to normalization queue size is: {ingestion_to_normalization_queue.qsize()}")
        else:
            logger.error(f"Skipping {name} as its results were empty")

    return ingestion_to_normalization_queue


if __name__ == "__main__":
    async def ingestion():
        q = asyncio.Queue()
        x = await main(q)
        for _ in range(x.qsize()):
            print(await x.get())

    asyncio.run(ingestion())