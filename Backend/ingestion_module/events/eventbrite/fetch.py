import re
import httpx
import asyncio
import aiofiles
import json
import logging
from lxml import html
from typing import Dict, List, Any

logger = logging.getLogger()

BASE_URL = "https://www.eventbrite.com/d"
LOCATION = "kenya"
SEARCH_FILTER = "ai"

SEARCH_URL = f"{BASE_URL}/{LOCATION}/{SEARCH_FILTER}/"
CLASS_WITH_DATA = 'Stack_root__1ksk7'

"""
Visit the search url. Then do an xpath for the class_with_data.
Get the <a> and <p> tags. Feed the info to the LLM. Retrieve
info based on data structure in utils/data_structures.
"""

async def fetch_eventbrite_events(client: httpx.AsyncClient, url: str)->Dict[str, List[Any]]:
    logger.info("Fetching Eventbrite events....")
    logger.info(f"The url is : {url}")
    event_data = {
        "type": "events",
        "source": "",
        "event_title": [],
        "event_link": [],
        "event_date": [],
        "event_country": [],
        "event_city": [],
        "event_id": [],
        "event_summary": [],
        "event_is_online": [],
        "event_tags": []
        }

    try:
        #Visit url and raise error msg if error happens
        response = await client.get(url)
        response.raise_for_status()

        #Look for window.__SERVER__DATA__
        match = re.search(r"window\.__SERVER_DATA__\s*=\s*(\{.*?})\s*;", response.text, re.DOTALL)
        if not match:
            logger.error("Could not find JSON data in page")
            raise ValueError("Could not find JSON data in page")


        raw_json = match.group(1)
        data = json.loads(raw_json)
        
        #Append event data in event_data dictionary
        events = data.get("search_data", {}).get("events", {}).get("results", [])
        for event in events:
            event_data["event_title"].append(event.get("name", ""))
            event_data["event_date"].append(event.get("start_date", ""))
            event_data["event_country"].append(event.get("timezone", "").split("/")[0])
            event_data["event_city"].append(event.get("timezone", "").split("/")[1])
            event_data["event_link"].append(event.get("url", ""))
            event_data["event_id"].append(event.get("eventbrite_event_id", ""))
            event_data["event_summary"].append(event.get("summary", ""))
            event_data["event_is_online"].append(event.get("is_online_event", "").lower() == "true")
            event_data["event_organizer_id"].append(event.get("primary_organizer_id", ""))
            event_tags = [tag.get("display_name", "") for tag in event.get("tags", [])]
            event_data["event_tags"].append(event_tags)

        event_data["source"] = "Eventbrite"

        logger.info("Done fetching Eventbrite events")

        logger.info("Logging eventbrite info to file")
        async with aiofiles.open("eventbrite_data.txt", "a") as file:
            await file.writelines(json.dumps(event_data, indent=2))
        logger.info("Done logging eventbrite info to file")

        return event_data

    except Exception as e:
        logger.error(f"Error fetching eventbrite events: {str(e)}")
        return event_data

async def main():
    async with httpx.AsyncClient() as client:
        return await fetch_eventbrite_events(client, SEARCH_URL)

if __name__ == "__main__":
    asyncio.run(main())

