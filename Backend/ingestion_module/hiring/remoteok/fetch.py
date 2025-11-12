"""
RemoteOK Hiring Ingestion Module
--------------------------------
Fetches remote job listings from RemoteOK using their public sitemap index as the
authoritative inventory of active postings, enriches each entry with metadata from
the RemoteOK JSON API, and forwards the structured payload to the AI extraction
pipeline.
"""

import asyncio
import copy
import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import httpx

from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from utils.data_structures.hiring_data_structure import (
    fetched_hiring_data as hiring_fetched_data,
)

logger = logging.getLogger(__name__)

REMOTEOK_SITEMAP_INDEX_URL = "https://remoteok.com/sitemap.xml"
REMOTEOK_API_URL = "https://remoteok.com/api"
USER_AGENT = "AI-ML-Lead-Gen/1.0 (+https://github.com/)"

SITEMAP_CONCURRENCY = 5
JOB_DETAIL_CONCURRENCY = 8
API_TIMEOUT_SECONDS = 30.0
RECENT_DAYS_WINDOW = 60
MAX_LISTINGS = 200  # Safety guard so we do not overwhelm downstream processing

_sitemap_semaphore = asyncio.Semaphore(SITEMAP_CONCURRENCY)
_job_detail_semaphore = asyncio.Semaphore(JOB_DETAIL_CONCURRENCY)


def _normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    normalized = url.strip()
    if "#" in normalized:
        normalized = normalized.split("#", 1)[0]
    if "?" in normalized:
        normalized = normalized.split("?", 1)[0]
    return normalized.rstrip("/")


def _strip_html(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


class RemoteOKDescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self._depth = 0
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "div":
            attr_dict = {name: (value or "") for name, value in attrs}
            classes = attr_dict.get("class", "")
            class_tokens = set(classes.split())
            if (
                not self._capture
                and "description" in class_tokens
                and attr_dict.get("itemprop") == "description"
            ):
                self._capture = True
                self._depth = 1
                return

        if self._capture:
            self._depth += 1
            if tag in {"p", "br", "div", "li", "h1", "h2", "h3"}:
                self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._capture:
            return

        self._depth -= 1
        if tag in {"p", "div", "li"}:
            self._parts.append("\n")

        if self._depth <= 0:
            self._capture = False
            self._depth = 0

    def handle_data(self, data: str) -> None:
        if self._capture and data:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _extract_description_from_html(html: str) -> str:
    parser = RemoteOKDescriptionParser()
    parser.feed(html)
    description = parser.get_text()
    parser.close()
    return description


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        sanitized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(sanitized)
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        logger.debug(f"Unable to parse ISO datetime value: {value}")
        return None


def _parse_epoch(epoch_value: Optional[Any]) -> Optional[datetime]:
    if epoch_value is None:
        return None
    try:
        return datetime.fromtimestamp(float(epoch_value), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _is_recent(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RECENT_DAYS_WINDOW)
    return dt >= cutoff


async def _fetch_with_semaphore(client: httpx.AsyncClient, url: str) -> Optional[str]:
    async with _sitemap_semaphore:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml"},
                timeout=API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.text
        except Exception as exc:
            logger.error(f"Failed to fetch sitemap '{url}': {exc}")
            return None


async def _fetch_sitemap_index(client: httpx.AsyncClient) -> List[str]:
    text = await _fetch_with_semaphore(client, REMOTEOK_SITEMAP_INDEX_URL)
    if not text:
        return []

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        logger.error(f"Unable to parse RemoteOK sitemap index: {exc}")
        return []

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls: List[str] = []
    for loc in root.findall("sm:sitemap/sm:loc", namespace):
        href = loc.text.strip() if loc.text else ""
        if "sitemap-jobs" in href:
            sitemap_urls.append(href)

    if not sitemap_urls:
        logger.warning("No job sitemaps discovered in RemoteOK sitemap index.")
    else:
        logger.info(f"Discovered {len(sitemap_urls)} RemoteOK job sitemap shards.")

    return sitemap_urls


async def _fetch_job_sitemap(client: httpx.AsyncClient, sitemap_url: str) -> List[Tuple[str, Optional[datetime]]]:
    text = await _fetch_with_semaphore(client, sitemap_url)
    if not text:
        return []

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        logger.error(f"Unable to parse job sitemap '{sitemap_url}': {exc}")
        return []

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    job_entries: List[Tuple[str, Optional[datetime]]] = []
    for url_node in root.findall("sm:url", namespace):
        loc_node = url_node.find("sm:loc", namespace)
        if loc_node is None or not loc_node.text:
            continue
        job_url = _normalize_url(loc_node.text)
        if not job_url:
            continue

        lastmod_node = url_node.find("sm:lastmod", namespace)
        lastmod_dt = _parse_iso_datetime(lastmod_node.text.strip()) if lastmod_node is not None and lastmod_node.text else None
        job_entries.append((job_url, lastmod_dt))

    return job_entries


async def _collect_recent_job_urls(client: httpx.AsyncClient) -> Dict[str, Dict[str, Any]]:
    sitemap_urls = await _fetch_sitemap_index(client)
    if not sitemap_urls:
        return {}

    tasks = [_fetch_job_sitemap(client, url) for url in sitemap_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    recent_jobs: Dict[str, Dict[str, Any]] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Job sitemap retrieval failed: {result}")
            continue
        for job_url, lastmod_dt in result:
            if lastmod_dt and not _is_recent(lastmod_dt):
                continue
            normalized_url = _normalize_url(job_url)
            if not normalized_url:
                continue
            if normalized_url not in recent_jobs or (
                lastmod_dt and recent_jobs[normalized_url].get("lastmod_dt") and lastmod_dt > recent_jobs[normalized_url]["lastmod_dt"]
            ):
                recent_jobs[normalized_url] = {
                    "source_url": job_url,
                    "lastmod_dt": lastmod_dt,
                    "lastmod": lastmod_dt.isoformat() if lastmod_dt else None,
                }

    logger.info(f"Identified {len(recent_jobs)} recent RemoteOK job URLs from sitemaps.")
    return recent_jobs


async def _fetch_remoteok_api(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    try:
        response = await client.get(
            REMOTEOK_API_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        logger.error("Unexpected payload structure from RemoteOK API (expected list).")
        return []
    except Exception as exc:
        logger.error(f"Failed to fetch RemoteOK API payload: {exc}")
        return []


async def _fetch_job_page(
    client: httpx.AsyncClient, url: str
) -> Tuple[str, Optional[str], Optional[str]]:
    async with _job_detail_semaphore:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            html = response.text
            description = _extract_description_from_html(html)
            return url, html, description
        except Exception as exc:
            logger.debug(f"Failed to fetch RemoteOK job detail page '{url}': {exc}")
            return url, None, None


def _build_job_page_queue(remoteok_jobs: List[Dict[str, Any]]) -> List[Tuple[str, Optional[str]]]:
    queue: List[Tuple[str, Optional[str]]] = []
    seen: set[str] = set()

    for job in remoteok_jobs:
        job_url = _normalize_url(job.get("url") or job.get("apply_url") or job.get("original") or "")
        slug = job.get("slug")
        if not job_url and slug:
            job_url = _normalize_url(f"https://remoteok.com/remote-jobs/{slug}")
        if not job_url:
            continue
        if job_url in seen:
            continue
        seen.add(job_url)
        queue.append((job_url, slug if isinstance(slug, str) else None))
        if len(queue) >= MAX_LISTINGS * 2:
            break

    return queue


async def _fetch_job_pages(
    client: httpx.AsyncClient, remoteok_jobs: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Optional[str]]]:
    queue = _build_job_page_queue(remoteok_jobs)
    if not queue:
        return {}

    tasks = [_fetch_job_page(client, url) for url, _ in queue]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    pages: Dict[str, Dict[str, Optional[str]]] = {}
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.debug(f"Job detail fetch raised exception: {result}")
            continue

        url, html, description = result
        if not html and not description:
            continue

        slug = queue[idx][1]
        candidates = {url, url.rstrip("/")}
        if slug:
            canonical_slug_url = _normalize_url(f"https://remoteok.com/remote-jobs/{slug}")
            if canonical_slug_url:
                candidates.add(canonical_slug_url)
                candidates.add(canonical_slug_url.rstrip("/"))

        for candidate in candidates:
            if candidate and candidate not in pages:
                pages[candidate] = {"html": html, "description": description}

    return pages


def _build_job_postings(
    remoteok_jobs: List[Dict[str, Any]],
    sitemap_jobs: Dict[str, Dict[str, Any]],
    job_pages: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
) -> Dict[str, List[Any]]:
    postings: Dict[str, List[Any]] = {"ids": [], "urls": [], "titles": [], "metadata": []}

    for job in remoteok_jobs:
        job_id_raw = job.get("id")
        if isinstance(job_id_raw, str) and job_id_raw.lower() == "legal":
            # Skip the metadata/legal disclaimer object included in the API payload
            continue

        job_id = job_id_raw or job.get("slug")
        if not job_id:
            continue

        job_url = _normalize_url(job.get("url") or job.get("apply_url") or job.get("original") or "")
        slug = job.get("slug")
        if not job_url and slug:
            job_url = _normalize_url(f"https://remoteok.com/remote-jobs/{slug}")

        if not job_url:
            continue

        lastmod_dt = None
        sitemap_entry = None
        if sitemap_jobs:
            sitemap_entry = sitemap_jobs.get(job_url)
            if not sitemap_entry:
                sitemap_entry = sitemap_jobs.get(job_url.rstrip("/"))
            if not sitemap_entry and slug:
                # RemoteOK sitemap URLs are always lower-case slugs with the pattern /remote-jobs/<slug>
                fallback_url = _normalize_url(f"https://remoteok.com/remote-jobs/{slug}")
                if fallback_url:
                    sitemap_entry = sitemap_jobs.get(fallback_url) or sitemap_jobs.get(fallback_url.rstrip("/"))
        if sitemap_entry:
            lastmod_dt = sitemap_entry.get("lastmod_dt")

        # Check recency using API fields if sitemap did not include it
        epoch_dt = _parse_epoch(job.get("epoch"))
        date_dt = _parse_iso_datetime(job.get("date"))
        posted_dt = epoch_dt or date_dt or lastmod_dt
        if not _is_recent(posted_dt):
            continue

        company = job.get("company") or job.get("company_name")
        position = job.get("position") or job.get("title")
        if not position:
            continue

        location = job.get("location") or job.get("location_raw") or job.get("office") or ""
        page_data: Optional[Dict[str, Optional[str]]] = None
        if job_pages:
            page_data = job_pages.get(job_url) or job_pages.get(job_url.rstrip("/"))
            if not page_data and slug:
                slug_url = _normalize_url(f"https://remoteok.com/remote-jobs/{slug}")
                if slug_url:
                    page_data = job_pages.get(slug_url) or job_pages.get(slug_url.rstrip("/"))

        description_html = (
            job.get("description")
            or job.get("full_description")
            or (page_data.get("html") if page_data else "")
            or ""
        )
        page_description = (page_data or {}).get("description")
        description = page_description or _strip_html(description_html)
        if len(description) > 3000:
            description = description[:3000] + "..."

        tags = job.get("tags") or job.get("department") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []

        salary_metadata_raw = {
            "min": job.get("salary_min") or job.get("salaryMin"),
            "max": job.get("salary_max") or job.get("salaryMax"),
            "currency": job.get("currency") or job.get("salary_currency"),
            "period": job.get("salary_period") or job.get("salaryPeriod"),
            "median": job.get("salary_median") or job.get("salaryMedian"),
            "raw": job.get("salary") or job.get("compensation"),
            "extra": job.get("salary_extra") or job.get("salaryExtra"),
        }
        salary_metadata = {
            key: value
            for key, value in salary_metadata_raw.items()
            if value not in (None, "", [], {})
        }

        salary_snippet = ""
        if salary_metadata.get("min") is not None and salary_metadata.get("max") is not None:
            salary_snippet = f"Salary: {salary_metadata['min']} - {salary_metadata['max']}"
        elif salary_metadata.get("raw"):
            salary_snippet = f"Salary: {salary_metadata['raw']}"

        formatted_title = position
        if company:
            formatted_title += f" at {company}"
        if location:
            formatted_title += f" ({location})"
        if salary_snippet:
            formatted_title += f" | {salary_snippet}"
        if description:
            formatted_title += f" | {description[:200]}{'...' if len(description) > 200 else ''}"

        location_metadata = {
            "formatted": location,
            "city": job.get("city"),
            "state": job.get("state"),
            "country": job.get("country"),
            "raw": location,
        }

        metadata = {
            "job_id": str(job_id),
            "job_title": position,
            "company": company,
            "location": location_metadata,
            "is_remote": True,
            "employment_type": job.get("type") or job.get("employment_type"),
            "employment_types": job.get("types") if isinstance(job.get("types"), list) else [],
            "posted_at": job.get("date"),
            "posted_at_timestamp": job.get("epoch"),
            "posted_at_text": job.get("date"),
            "publisher": "RemoteOK",
            "description": description,
            "highlights": {"tags": tags} if tags else {},
            "skills": tags,
            "salary": salary_metadata,
            "benefits": job.get("benefits") if isinstance(job.get("benefits"), list) else [],
            "apply_url": job_url,
            "apply_options": [],
            "apply_is_direct": True,
            "apply_secondary_links": job.get("apply_url") if job.get("apply_url") else None,
            "raw_source": "RemoteOK",
            "company_logo": job.get("logo") or job.get("company_logo"),
            "source_lastmod": sitemap_jobs.get(job_url, {}).get("lastmod") if sitemap_jobs else None,
            "page_html": page_data.get("html") if page_data else None,
            "page_description_text": page_description,
        }

        postings["ids"].append(str(job_id))
        postings["urls"].append(job_url)
        postings["titles"].append(formatted_title)
        postings["metadata"].append(metadata)

        if len(postings["ids"]) >= MAX_LISTINGS:
            logger.info(f"Reached MAX_LISTINGS limit of {MAX_LISTINGS}; stopping ingestion early.")
            break

    if not postings["ids"]:
        logger.warning("No RemoteOK job postings satisfied the filtering criteria.")

    return postings


def _deduplicate_postings(postings: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    seen_urls = set()
    deduped = {"ids": [], "urls": [], "titles": [], "metadata": []}

    for idx, url in enumerate(postings.get("urls", [])):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped["urls"].append(url)
        deduped["ids"].append(postings["ids"][idx])
        deduped["titles"].append(postings["titles"][idx])
        if len(postings.get("metadata", [])) > idx:
            deduped["metadata"].append(postings["metadata"][idx])

    return deduped


async def main() -> Dict[str, Any]:
    logger.info("Starting RemoteOK hiring data fetch...")
    start_time = datetime.now(tz=timezone.utc)

    async with httpx.AsyncClient() as client:
        sitemap_jobs = await _collect_recent_job_urls(client)
        api_jobs = await _fetch_remoteok_api(client)
        job_pages = await _fetch_job_pages(client, api_jobs) if api_jobs else {}

    if not api_jobs:
        logger.error("RemoteOK API returned no data; aborting RemoteOK ingestion.")
        return {}

    postings = _build_job_postings(api_jobs, sitemap_jobs, job_pages)
    postings = _deduplicate_postings(postings)

    if not postings["ids"]:
        logger.warning("RemoteOK produced no eligible postings after deduplication.")
        return {}

    logger.info(f"Preparing {len(postings['ids'])} RemoteOK jobs for AI extraction.")
    try:
        extracted_data = await finalize_ai_extraction(postings)
    except Exception as exc:
        logger.error(f"Failed to execute AI extraction for RemoteOK payload: {exc}")
        extracted_data = {}

    if not extracted_data:
        logger.warning("AI extraction returned no usable results for RemoteOK.")
        return {}

    llm_results = copy.deepcopy(hiring_fetched_data)
    for key, value in extracted_data.items():
        if key in llm_results and isinstance(llm_results[key], list):
            llm_results[key].extend(value)
        elif key in llm_results:
            llm_results[key] = value

    llm_results["source"] = "RemoteOK"
    llm_results["link"] = postings.get("urls", [])

    duration = datetime.now(tz=timezone.utc) - start_time
    logger.info(
        f"RemoteOK hiring ingestion completed in {duration.total_seconds():.2f} seconds "
        f"with {len(llm_results.get('article_id', []))} extracted articles."
    )

    return llm_results


if __name__ == "__main__":
    asyncio.run(main())


