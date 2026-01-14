import httpx
import asyncio
import json
import asyncpg
import logging
from typing import Dict, Any, List

from services.email_sending import send_email
from services.db_service import (
    fetch_uncontacted_people,
    fetch_company_by_apollo_id,
    get_hiring_area,
    store_email,
    fetch_people_by_ids
)
from outreach_module.ai_email_generation import call_gemini_api
from utils.prompts.email_generation_prompt import get_email_generation_prompt
from utils.find_missing_companies import find_missing_companies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Fetch phase
# ---------------------------------------------------------

async def fetch_people(pool) -> List[Dict[str, Any]]:
    logger.info("Fetching uncontacted people...")
    return await fetch_uncontacted_people(pool)


# ---------------------------------------------------------
# Processing phase (single person)
# ---------------------------------------------------------

async def process_person(person: Dict[str, Any], pool) -> bool:
    """
    Process a single person.

    Returns:
        True  -> processed successfully or intentionally skipped
        False -> company not found (needs retry)
    """
    persons_email = person.get("email", "")
    persons_company_apollo_id = person.get("organization_id", "")

    persons_company = await fetch_company_by_apollo_id(persons_company_apollo_id)

    if not persons_company:
        logger.warning(
            f"No company found for {person.get('first_name', 'Unknown')}, id = {person.get("id")}"
            f"(apollo_id={persons_company_apollo_id})"
        )
        return False

    company_description = persons_company.get("short_description")
    data_source = persons_company.get("company_data_source", "")
    latest_funding_round = persons_company.get("latest_funding_round", "latest")
    first_name = person.get("first_name")
    company_name = persons_company.get("name")

    if data_source == "funding":
        prompt = get_email_generation_prompt(
            company_description=company_description,
            first_name=first_name,
            company_name=company_name,
            trigger_type=data_source,
            funding_round=latest_funding_round,
        )
    elif data_source == "hiring":
        hiring_area = await get_hiring_area(company_name, pool) or "various areas"
        prompt = get_email_generation_prompt(
            company_description=company_description,
            first_name=first_name,
            company_name=company_name,
            trigger_type=data_source,
            hiring_area=hiring_area,
        )
    else:
        logger.warning(f"Unknown data source {data_source} for {company_name}")
        return True

    ai_response = await call_gemini_api(prompt)

    try:
        email_json = json.loads(ai_response.text)
    except json.JSONDecodeError:
        logger.error("Invalid json from llm for person_id = %r", person.get("id"))
        return True
        
    email_subject=email_json["subject"]
    email_content=email_json["content"]

    # Email Sending
    # response = await send_email(
    #     email_to=persons_email,
    #     subject=email_subject,
    #     content=email_content,
    # )

    # Store email
    await store_email(
        pool,
        recipient_id=person.get("id"),
        company_id=persons_company.get("id"),
        subject=email_subject,
        body=email_content
    )

    return True

# ---------------------------------------------------------
# Processing phase (batch)
# ---------------------------------------------------------

async def process_people(
    people: List[Dict[str, Any]],
    pool,
) -> List[str]:
    """
    Process a batch of people.

    Returns:
        List of organization_ids that were missing
    """
    unfound_people: List[dict[str, str | int]] = []

    for person in people:
        try:
            success = await process_person(person, pool)
            if not success:
                org_id = person.get("organization_id")

                if org_id:
                    unfound_person_details = {}
                    unfound_person_details["id"] = person.get("id", '')
                    unfound_person_details["organization_id"] = person.get("organization_id", '')
                    unfound_people.append(unfound_person_details)

        except Exception as e:
            logger.exception(
                f"Failed processing {person.get('first_name', 'Unknown')}: {e}"
            )

    return unfound_people

# ---------------------------------------------------------
# Resolution phase
# ---------------------------------------------------------

async def resolve_missing_companies(
    unfound_people: List[Dict[str, str | int]],
    pool,
):
    if not unfound_people:
        return

    logger.info(f"Resolving {len(unfound_people)} missing companies...")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        org_ids = []
        for unfound_person in unfound_people:
            org_id = unfound_person.get("organization_id")
            org_ids.append(org_id)

        await find_missing_companies(
            pool,
            client,
            organization_ids=org_ids,
        )


# ---------------------------------------------------------
# Retry phase
# ---------------------------------------------------------

async def retry_unfound_people(
    unfound_people:List[Dict[str, str | int]],
    pool,
):
    if not unfound_people:
        return

    logger.info("Retrying people after company resolution...")

    ids = []
    for person in unfound_people:
        persons_id = person.get('id')
        ids.append(persons_id)
        
    people_to_retry = await fetch_people_by_ids(pool, ids)

    await process_people(people_to_retry, pool)


# ---------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------

async def main(pool):
    logger.info("Starting outreach pipeline...")

    people = await fetch_people(pool)

    unfound_people = await process_people(people, pool)

    if unfound_people:
        await resolve_missing_companies(unfound_people, pool)
        await retry_unfound_people(unfound_people, pool)

    logger.info("Email sending complete")


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv(override=True)
    DB_URL = os.getenv("MOCK_DATABASE_URL")

    async def mainn():
        async with asyncpg.create_pool(
            dsn=DB_URL,
            min_size=1,
            max_size=100,
        ) as pool:
            await main(pool)

    asyncio.run(mainn())
