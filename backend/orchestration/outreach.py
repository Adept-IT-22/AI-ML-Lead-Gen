import httpx
import asyncio
import json
import asyncpg
import logging
from typing import Dict, Any, List, Optional

from services.email_sending import send_email
from services.db_service import (
    fetch_eligible_people,
    fetch_company_by_apollo_id,
    get_hiring_area,
    get_painpoints,
    fetch_funding_details,
    store_email,
    fetch_people_by_ids,
)
from outreach_module.ai_email_generation import call_gemini_api
from utils.prompts.email_generation_prompt import get_email_generation_prompt
from utils.find_missing_companies import find_missing_companies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETRY_LIMIT_PER_DAY = 500


# ---------------------------------------------------------
# Fetch phase
# ---------------------------------------------------------

async def fetch_people_for_discovery(
    pool,
    organization_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    logger.info(f"Fetching discovery people (scoped to {len(organization_ids) if organization_ids else 'ALL'} orgs)")
    return await fetch_eligible_people(pool, organization_ids=organization_ids)


async def fetch_people_for_retry(
    pool,
    limit: int,
) -> List[Dict[str, Any]]:
    logger.info("Fetching retry people (global backlog)")
    people = await fetch_eligible_people(pool, organization_ids=None)
    return people[:limit]


# ---------------------------------------------------------
# Processing phase (single person)
# ---------------------------------------------------------

async def process_person(person: Dict[str, Any], pool) -> bool:
    """
    Returns:
        True  -> processed or intentionally skipped
        False -> company missing (needs resolution)
    """
    person_id = person.get("id")
    first_name = person.get("first_name")
    email = person.get("email", "")
    org_apollo_id = person.get("organization_id", "")
    unsubscribe_token = person.get("unsubscribe_token", "")
    sequence_number = person.get("times_contacted", 0) + 1

    company = await fetch_company_by_apollo_id(org_apollo_id)

    if not company:
        logger.warning(
            "Company missing for person_id=%s (org_apollo_id=%s)",
            person_id,
            org_apollo_id,
        )
        return False

    company_id = company.get("id")
    company_name = company.get("name")
    company_description = company.get("short_description")
    data_source = company.get("company_data_source", "")
    funding_round = company.get("latest_funding_round", "latest")

    hiring_area = None
    painpoints = []
    if data_source == "hiring":
        hiring_area = await get_hiring_area(company_name, pool)
        painpoints = await get_painpoints(company_name, pool, "hiring")
    
    elif data_source == "funding":
        painpoints = await get_painpoints(company_name, pool, "funding")

    if data_source not in {"funding", "hiring"}:
        logger.warning(
            "Unknown data source '%s' for company %s",
            data_source,
            company_name,
        )
        return True

    prompt = get_email_generation_prompt(
        company_description=company_description,
        first_name=first_name,
        company_name=company_name,
        trigger_type=data_source,
        sequence_number=sequence_number,
        funding_round=funding_round,
        hiring_area=hiring_area,
        painpoints=painpoints
    )

    ai_response = await call_gemini_api(prompt)

    try:
        text = ai_response.candidates[0].content.parts[0].text
        email_json = json.loads(text)
    except Exception:
        logger.error("Invalid LLM output for person_id=%s", person_id)
        return True

    subject = email_json["subject"].format(
        first_name=first_name,
        company_name=company_name,
        company_description=company_description,
        hiring_area=hiring_area,
        funding_round=funding_round,
    )

    content = email_json["content"].format(
        first_name=first_name,
        company_name=company_name,
        company_description=company_description,
        hiring_area=hiring_area,
        funding_round=funding_round,
    )

    # ⚠️ Email sending intentionally disabled!
    # await send_email(
    #     email_to=email,
    #     subject=subject,
    #     content=content,
    #     unsubscribe_token=unsubscribe_token,
    # )

    await store_email(
        pool,
        recipient_id=person_id,
        company_id=company_id,
        subject=subject,
        body=content,
        sequence_number=sequence_number,
    )

    return True


# ---------------------------------------------------------
# Processing phase (batch)
# ---------------------------------------------------------

async def process_people(
    people: List[Dict[str, Any]],
    pool,
) -> List[Dict[str, str | int]]:
    if not people:
        logger.info("No eligible people found")
        return []

    unfound_people: List[Dict[str, str | int]] = []

    for person in people:
        org_id = person.get("organization_id")

        try:
            success = await process_person(person, pool)
            if not success and org_id:
                unfound_people.append(
                    {
                        "id": person.get("id"),
                        "organization_id": org_id,
                    }
                )
        except Exception:
            logger.exception(
                "Failed processing %s from org_id=%s",
                person.get("first_name", "Unknown"),
                org_id,
            )

    return unfound_people


# ---------------------------------------------------------
# Resolution + retry helpers
# ---------------------------------------------------------

async def resolve_missing_companies(
    unfound_people: List[Dict[str, str | int]],
    pool,
):
    if not unfound_people:
        return

    org_ids = list(
        {p["organization_id"] for p in unfound_people if p.get("organization_id")}
    )

    logger.info("Resolving %d missing companies", len(org_ids))

    async with httpx.AsyncClient(timeout=30.0) as client:
        await find_missing_companies(
            pool,
            client,
            organization_ids=org_ids,
        )


async def retry_unfound_people(
    unfound_people: List[Dict[str, str | int]],
    pool,
):
    if not unfound_people:
        return

    ids = [p["id"] for p in unfound_people if p.get("id")]
    people = await fetch_people_by_ids(pool, ids)
    await process_people(people, pool)


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def dedupe_people(people: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for person in people:
        pid = person.get("id")
        if pid and pid not in seen:
            seen.add(pid)
            result.append(person)

    return result


# ---------------------------------------------------------
# Main orchestrator (daily run)
# ---------------------------------------------------------

async def main(
    pool,
    organization_ids: Optional[List[str]] = None,
):
    logger.info("Starting daily outreach run")

    discovery_people = await fetch_people_for_discovery(
        pool,
        organization_ids,
    )

    #retry_people = await fetch_people_for_retry(
        #pool,
        #limit=RETRY_LIMIT_PER_DAY,
    #)

    #people_to_contact = dedupe_people(discovery_people + retry_people)

    people_to_contact = discovery_people

    logger.info(
        #"People to contact today: discovery=%d retry=%d total=%d",
        "People to contact today: discovery=%d total=%d",
        len(discovery_people),
        #len(retry_people),
        len(people_to_contact),
    )

    unfound_people = await process_people(people_to_contact, pool)

    if unfound_people:
        logger.warning("Found %d people with missing companies", len(unfound_people))
        # await resolve_missing_companies(unfound_people, pool)
        # await retry_unfound_people(unfound_people, pool)

    logger.info("Daily outreach run complete")


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv(override=True)
    DB_URL = os.getenv("MOCK_DATABASE_URL")

    async def runner():
        async with asyncpg.create_pool(
            dsn=DB_URL,
            min_size=1,
            max_size=100,
        ) as pool:
            await main(pool)

    asyncio.run(runner())
