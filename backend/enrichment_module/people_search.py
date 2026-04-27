import time
import httpx
import logging
import asyncio
from typing import Dict, Any, List
from config.apollo_config import headers as APOLLO_HEADERS
from helpers.apollo_rate_limiter import rate_limited_apollo_call

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
MAX_BEST_CONTACTS = 3  # Enrichment credit cap per company

# ---------------------------------------------------------------------------
# Title priority scoring — lower score = higher priority.
# Titles not in this map receive a score of 99 (still accepted, lowest prio).
# The People Search endpoint is free (no credits), so we fetch 10 candidates
# and rank locally to guarantee the best 3 are sent to enrichment (which does
# cost credits — 1 per person revealed).
# ---------------------------------------------------------------------------
TITLE_PRIORITY: Dict[str, int] = {
    # Founders / owners
    "founder": 1,
    "co-founder": 1,
    "owner": 1,
    "partner": 2,
    # C-suite
    "ceo": 3,
    "chief executive officer": 3,
    "president": 3,
    "cto": 4,
    "chief technology officer": 4,
    "chief technological officer": 4,
    "cpo": 5,
    "chief product officer": 5,
    "coo": 6,
    "chief operating officer": 6,
    # VP / Head
    "vp of engineering": 10,
    "head of engineering": 10,
    "vp of ai": 10,
    "head of ai": 10,
    "head of machine learning": 10,
    "head of data science": 10,
    "vp of sales": 11,
    "head of sales": 11,
    "vp of marketing": 12,
    "head of marketing": 12,
    "vp of operations": 13,
    "head of operations": 13,
    # Director
    "director of engineering": 20,
    "director of sales": 21,
    "director of marketing": 22,
    # Manager / Senior (catch-all)
    "senior manager": 29,
    "senior software engineer": 29,
    "senior software developer": 29,
    "manager": 30,
}

def _title_score(person: Dict[str, Any]) -> int:
    """Return a priority score for a person based on their title.
    Lower is better. Checks the ``title`` field (case-insensitive).
    """
    raw_title: str = (person.get("title") or "").lower().strip()
    # Exact match first
    if raw_title in TITLE_PRIORITY:
        return TITLE_PRIORITY[raw_title]
    # Substring match — e.g. "VP of Engineering (EMEA)" → "vp of engineering"
    for key, score in TITLE_PRIORITY.items():
        if key in raw_title:
            return score
    return 99  # Unknown title — still included, lowest priority


def _select_best_contacts(
    people: List[Dict[str, Any]],
    max_contacts: int = MAX_BEST_CONTACTS,
) -> List[Dict[str, Any]]:
    """Sort *people* by title priority and return the top *max_contacts*."""
    return sorted(people, key=_title_score)[:max_contacts]


async def no_rate_limit_people_search(
        client: httpx.AsyncClient,
        org_ids: List[str],
        org_domains: List[str],
        api_url: str = PEOPLE_SEARCH_URL,
        headers: Dict[str, str] = APOLLO_HEADERS
    ) -> Dict[str, Any]:
    logger.info("Performing people search for %r...", org_domains)

    # Clean org_ids and org_domains to remove None values
    org_ids = [oid for oid in org_ids if oid]
    org_domains = [od for od in org_domains if od]

    # People Search is free (no credits). Fetch 10 candidates so the local
    # ranker has enough variety to pick the best 3. Only those 3 are passed
    # to enrichment, which is where credits are actually spent.
    payload = {
        "person_seniorities": [
            "owner", "founder", "c_suite", "partner",
            "vp", "head", "director", "manager", "senior"
        ],
        "contact_email_status": ["verified", "unverified", "likely_to_engage"],
        "organization_ids": org_ids,
        "q_organization_domains_list": org_domains,
        "page": 1,
        "per_page": 10,
    }

    try:
        # API call then check for errors
        response = await client.post(
            url=api_url,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"Apollo API Error {response.status_code}: {response.text}")

        response.raise_for_status()

        data: Dict[str, Any] = response.json()
        raw_people: List[Dict[str, Any]] = data.get("people", [])

        best_people = _select_best_contacts(raw_people)
        data["people"] = best_people

        logger.info(
            "People search complete — %d candidates → %d selected for enrichment for %r",
            len(raw_people), len(best_people), org_domains,
        )
        return data

    except Exception as e:
        logger.error(f"Couldn't perform people search: {str(e)}")
        return {"error": str(e)}


async def people_search(
        client: httpx.AsyncClient,
        org_ids: List[str],
        org_domains: List[str],
        api_url: str = PEOPLE_SEARCH_URL,
        headers: Dict[str, str] = APOLLO_HEADERS
    ) -> Dict[str, Any]:

    return await rate_limited_apollo_call(
        no_rate_limit_people_search, client, org_ids, org_domains, api_url, headers
    )


if __name__ == "__main__":
    async def main():
        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await people_search(
                client=client,
                org_ids=["5ed22dc60fc35b0001c2574c"],
                org_domains=["usecanopy.com"]
            )
            logger.info(f"People search results are: \n{results}")

        duration = time.perf_counter() - start_time
        logger.info(f"This task took {duration:.2f} seconds")

    asyncio.run(main())