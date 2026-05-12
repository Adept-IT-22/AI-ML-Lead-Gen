import os
import time
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict, Union

import httpx
from google.auth import default
from google.auth.transport.requests import Request

from utils.prompts.hiring_prompt import get_hiring_extraction_prompt

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Environment variables
# -------------------------------------------------------------------
load_dotenv(verbose=True, override=True)

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
if not PROJECT_ID:
    raise ValueError("GCP_PROJECT_ID not set")

REGION = os.getenv("GCP_REGION", "us-central1")
MODEL_NAME = "gemini-2.0-flash"

VERTEX_ENDPOINT = (
    f"https://{REGION}-aiplatform.googleapis.com/v1/"
    f"projects/{PROJECT_ID}/locations/{REGION}/"
    f"publishers/google/models/{MODEL_NAME}:generateContent"
)

BATCH_SIZE = 4
MAX_CONCURRENT_REQUEST = 1
semaphore = None  # Lazy initialized

RATE_LIMIT_SECONDS = 6
gemini_lock = None  # Lazy initialized
last_call: float = 0.0

# -------------------------------------------------------------------
# Auth helper
# -------------------------------------------------------------------
def get_access_token() -> str:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token

# -------------------------------------------------------------------
# Retry logic
# -------------------------------------------------------------------
def retry_if_resource_exhausted(exception: BaseException) -> bool:
    msg = str(exception).lower()
    return "429" in msg or "quota" in msg or "limit" in msg

def log_before_retry(retry_state: RetryCallState):
    logger.info(f"Retrying Gemini API call... attempt #{retry_state.attempt_number}")

def log_after(retry_state: RetryCallState):
    logger.info(f"Attempt #{retry_state.attempt_number} done")

def log_failure(retry_state: RetryCallState):
    logger.error(f"Gemini API failed after retries. Last exception: {retry_state.outcome.exception()}")
    return ""

# -------------------------------------------------------------------
# Vertex AI Gemini call with retry
# -------------------------------------------------------------------
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_resource_exhausted,
    reraise=True,
    before=log_before_retry,
    after=log_after,
    retry_error_callback=log_failure
)
async def _call_gemini_api_with_retry(prompt: str) -> str:
    logger.info("Attempting Gemini API call for hiring...")

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(VERTEX_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    if "candidates" not in data or not data["candidates"]:
        logger.error(f"Gemini response missing candidates. Data: {str(data)[:500]}")
        raise ValueError("Gemini response missing candidates")

    return data["candidates"][0]["content"]["parts"][0]["text"]

# -------------------------------------------------------------------
# Rate limiting wrapper
# -------------------------------------------------------------------
async def rate_limited_gemini_call(prompt: str):
    global last_call, gemini_lock
    if gemini_lock is None:
        gemini_lock = asyncio.Lock()
    async with gemini_lock:
        now = asyncio.get_running_loop().time()
        elapsed = now - last_call
        if elapsed < RATE_LIMIT_SECONDS:
            await asyncio.sleep(RATE_LIMIT_SECONDS - elapsed)
        last_call = asyncio.get_running_loop().time()
    return await _call_gemini_api_with_retry(prompt)

async def safe_process_hiring_data_batch(batch: Dict[str, List[Any]]):
    global semaphore
    if semaphore is None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)
    async with semaphore:
        return await process_hiring_data_batch(batch)

# -------------------------------------------------------------------
# Batch splitting
# -------------------------------------------------------------------
def split_into_batches(ids_urls_titles: Dict[str, List[str]], batch_size: int) -> List[Dict[str, List[Any]]]:
    total_articles = len(ids_urls_titles["ids"])
    result = []
    for i in range(0, total_articles, batch_size):
        result.append({
            "ids": ids_urls_titles["ids"][i:i+batch_size],
            "urls": ids_urls_titles["urls"][i:i+batch_size],
            "titles": ids_urls_titles["titles"][i:i+batch_size]
        })
    return result

# -------------------------------------------------------------------
# Process batch
# -------------------------------------------------------------------
async def process_hiring_data_batch(batch: Dict[str, List[Union[str, int]]]) -> Dict[str, List[Any]]:
    logger.info("AI hiring information extraction starting...")

    return_data: Dict[str, Any] = {
        "type": "hiring",
        "source": [], "article_id": [], "title": [], "link": [],
        "article_date": [], "company_name": [], "city": [], "country": [],
        "company_decision_makers": [], "job_roles": [], "hiring_reasons": [], "tags": [], "painpoints": [], "service": [],
    }

    try:
        id_to_data_map: Dict[Union[str, int], Dict[str, Any]] = {}
        combined_input = ""

        for article_id, url, title in zip(batch["ids"], batch["urls"], batch["titles"]):
            id_to_data_map[article_id] = {"url": url, "title": title}
            combined_input += f"\n------ARTICLE START------\nArticle: {article_id}\nURL: {url}\nContent: {title}\n------ARTICLE END------\n"

        prompt = get_hiring_extraction_prompt(combined_input)
        response_text = await rate_limited_gemini_call(prompt)

        try:
            extracted_json_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e.msg}")
            return return_data

        # Map original URLs back
        num_articles = len(extracted_json_data.get("article_id", []))
        if "article_link" not in extracted_json_data:
            extracted_json_data["article_link"] = [""] * num_articles
        elif len(extracted_json_data["article_link"]) < num_articles:
            extracted_json_data["article_link"].extend([""] * (num_articles - len(extracted_json_data["article_link"])))

        for i in range(num_articles):
            article_id = extracted_json_data["article_id"][i]
            original_data = id_to_data_map.get(article_id, {})
            extracted_json_data["article_link"][i] = original_data.get("url", "")

        return extracted_json_data

    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        return return_data

# -------------------------------------------------------------------
# Finalize all batches
# -------------------------------------------------------------------
async def finalize_ai_extraction(ids_urls_titles: Dict[str, List[str]]) -> Dict[str, List[Any]]:
    final_results = {}
    try:
        batches = split_into_batches(ids_urls_titles, BATCH_SIZE)
        tasks = [safe_process_hiring_data_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        for result in results:
            for key, val in result.items():
                if key not in final_results:
                    final_results[key] = val
                elif isinstance(final_results[key], list) and isinstance(val, list):
                    final_results[key].extend(val)

        return final_results

    except Exception as e:
        logger.error(f"Failed to finalize batches: {str(e)}")
        return final_results

# -------------------------------------------------------------------
# Example test function
# -------------------------------------------------------------------
async def fake_prompt(n):
    start = time.perf_counter()
    await rate_limited_gemini_call(f"Fake hiring prompt {n}")
    end = time.perf_counter()
    print(f"Task {n} finished in {end - start:.2f}s")

async def main():
    tasks = [fake_prompt(i) for i in range(5)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
