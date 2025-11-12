import os
import time
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict, Union, Optional
import google.generativeai as genai
from google.generativeai import types
from google.api_core.exceptions import ResourceExhausted
from utils.prompts.hiring_prompt import get_hiring_extraction_prompt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

#Import env variables
load_dotenv(verbose=True, override=True)

#Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found in env variables")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
)

BATCH_SIZE = 4 #How many jobs we want to feed the llm at a time

#=============REQUEST CONCURRENCY==============
MAX_CONCURRENT_REQUEST = 1 #How many API request we can send the llm at a time
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

#============API RATE LIMITS==============
RATE_LIMIT_SECONDS = 6
gemini_lock = asyncio.Lock()
last_call = 0   

async def rate_limited_gemini_call(prompt: str):
    global last_call
    async with gemini_lock:
        now = asyncio.get_running_loop().time()
        elapsed = now - last_call

        if elapsed < RATE_LIMIT_SECONDS:
            sleep_time = RATE_LIMIT_SECONDS - elapsed
            logger.info(f"Rate limiting in effect, sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        last_call = asyncio.get_running_loop().time()  # Update AFTER waiting
        return await _call_gemini_api_with_retry(prompt)

#Wrapper around process_article_batch to enforce the semaphore
async def safe_process_hiring_data_batch(batch: Dict[str, List[Any]]):
    async with semaphore:
        return await process_hiring_data_batch(batch)

#======================SPLIT DATA INTO BATCHES===========================
def split_into_batches(job_payload: Dict[str, List[Any]], batch_size: int) -> List[Dict[str, List[Any]]]:
    logger.info("Splitting hiring data into batches...")
    ids = job_payload.get("ids", [])
    total_articles = len(ids)
    if total_articles == 0:
        return []

    keys = list(job_payload.keys())
    result = []
    for i in range(0, total_articles, batch_size):
        batch: Dict[str, List[Any]] = {}
        for key in keys:
            values = job_payload.get(key, [])
            if not values:
                continue
            batch[key] = values[i:i + batch_size]
        result.append(batch)
    logger.info("Splitting hiring data into batches done")
    return result

#===============================HANDLE RETRIES====================================
#Check if exception is a ResourceExhaustedException
def retry_if_resource_exhausted(exception: BaseException) -> bool:
    """Returns True if the exception is a ResourceExhausted exception."""
    return isinstance(exception, ResourceExhausted)


def log_before_retry(retry_state: RetryCallState):
    logger.info(f"Retrying Gemini API call... attempt #{retry_state.attempt_number}")

def log_after(retry_state: RetryCallState):
    logger.info(f"Attempt #{retry_state.attempt_number} done")

def log_failure():
    logger.error("Gemini API failed after retries.")
    return

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_resource_exhausted,
    reraise=True,
    before=log_before_retry,
    after=log_after,
    retry_error_callback=log_failure
)
async def _call_gemini_api_with_retry(prompt: str) -> types.GenerateContentResponse:
    """Internal function to call Gemini API with retry logic."""
    logger.info("Attempting Gemini API call for hiring...")
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                contents=prompt,
                generation_config=types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.5,
                )
            ),
            timeout=30.0
        )
        logger.info("Gemini API for hiring call successful.")
        return response
    except Exception as e:
        logger.error(f"Gemini API call for hiring failed: {str(e)}")
        return

#=======================PROCESS EACH BATCH=========================
async def process_hiring_data_batch(batch: Dict[str, List[Union[str, int]]])->Dict[str, List[Any]]:
    logger.info("AI hiring information extraction beginning...")

    return_data = {
        "type": "hiring",
        "source": [],
        "article_id": [],
        "title": [],
        "link": [],
        "article_date": [],
        "company_name": [],
        "city": [],
        "country": [],
        "company_decision_makers": [],
        "job_roles": [],
        "hiring_reasons": [],
        "tags": []
    }

    try:
        id_to_data_map: Dict[Any, Dict[str, Any]] = {} #Maps every article ID to its payload
        combined_input_for_llm = ""

        ids: List[Any] = batch.get("ids", [])
        urls: List[str] = batch.get("urls", [])
        titles: List[str] = batch.get("titles", [])
        metadata_list: List[Dict[str, Any]] = batch.get("metadata", [])

        for index, article_id in enumerate(ids):
            url = urls[index] if index < len(urls) else ""
            title = titles[index] if index < len(titles) else ""
            metadata: Optional[Dict[str, Any]] = metadata_list[index] if index < len(metadata_list) else None

            id_to_data_map[article_id] = {"url": url, "title": title, "metadata": metadata}

            if metadata:
                job_title = metadata.get("job_title") or title
                company = metadata.get("company", "")
                location_info = metadata.get("location") or {}
                location_text = location_info.get("formatted") if isinstance(location_info, dict) else ""
                if not location_text and isinstance(location_info, dict):
                    location_parts = [
                        location_info.get("city"),
                        location_info.get("state"),
                        location_info.get("country"),
                    ]
                    location_text = ", ".join([part for part in location_parts if part])
                employment_type = metadata.get("employment_type") or metadata.get("employment_types")
                remote_status = metadata.get("is_remote")
                posted_at = metadata.get("posted_at") or metadata.get("posted_at_text")
                salary = metadata.get("salary") or {}
                salary_text = ""
                if isinstance(salary, dict):
                    min_salary = salary.get("min")
                    max_salary = salary.get("max")
                    median_salary = salary.get("median")
                    period = salary.get("period")
                    currency = salary.get("currency")
                    salary_components = []
                    if min_salary is not None or max_salary is not None:
                        if min_salary is not None and max_salary is not None:
                            salary_components.append(f"range: {min_salary} - {max_salary}")
                        elif min_salary is not None:
                            salary_components.append(f"minimum: {min_salary}")
                        elif max_salary is not None:
                            salary_components.append(f"maximum: {max_salary}")
                    if median_salary is not None:
                        salary_components.append(f"median: {median_salary}")
                    if currency:
                        salary_components.append(f"currency: {currency}")
                    if period:
                        salary_components.append(f"period: {period}")
                    if salary_components:
                        salary_text = ", ".join(salary_components)

                highlights = metadata.get("highlights") or {}
                formatted_highlights = ""
                if isinstance(highlights, dict) and highlights:
                    highlight_sections = []
                    for section, items in highlights.items():
                        if not items:
                            continue
                        if isinstance(items, list):
                            bullet_list = "\n".join([f"    - {item}" for item in items if item])
                        else:
                            bullet_list = f"    - {items}"
                        highlight_sections.append(f"{section}:\n{bullet_list}")
                    if highlight_sections:
                        formatted_highlights = "\n".join(highlight_sections)

                skills = metadata.get("skills") or []
                if isinstance(skills, list):
                    skills = [str(skill) for skill in skills if skill]
                else:
                    skills = [str(skills)] if skills else []

                job_description = metadata.get("description") or title
                if job_description:
                    job_description = str(job_description)
                    if len(job_description) > 2000:
                        job_description = job_description[:2000] + "..."

                apply_options = metadata.get("apply_options") or []
                apply_sections = []
                if isinstance(apply_options, list):
                    for option in apply_options:
                        if isinstance(option, dict):
                            publisher = option.get("publisher")
                            apply_link = option.get("apply_link")
                            is_direct = option.get("is_direct")
                            section_text = " | ".join(
                                [
                                    part
                                    for part in [
                                        f"publisher: {publisher}" if publisher else None,
                                        f"link: {apply_link}" if apply_link else None,
                                        f"is_direct: {is_direct}" if is_direct is not None else None,
                                    ]
                                    if part
                                ]
                            )
                            if section_text:
                                apply_sections.append(section_text)

                benefits = metadata.get("benefits")
                if isinstance(benefits, list):
                    benefits_text = ", ".join([str(b) for b in benefits if b])
                else:
                    benefits_text = str(benefits) if benefits else ""

                employment_text = ""
                if employment_type:
                    employment_text = employment_type if isinstance(employment_type, str) else ", ".join(
                        [str(t) for t in employment_type if t]
                    )

                combined_input_for_llm += f"""

                ------JOB START------
                Article ID: {article_id}
                URL: {url}
                Job Title: {job_title}
                Company: {company}
                Location: {location_text}
                Remote Status: {remote_status}
                Employment Type(s): {employment_text}
                Posted At: {posted_at}
                Publisher: {metadata.get("publisher", "")}
                Salary Info: {salary_text}
                Benefits: {benefits_text}
                Primary Apply URL: {metadata.get("apply_url", url)}
                Apply Options:
{chr(10).join([f"                    - {option}" for option in apply_sections]) if apply_sections else "                    - None provided"}
                Key Skills: {", ".join(skills) if skills else "None provided"}
                Skills & Highlights:
{formatted_highlights if formatted_highlights else "    - None provided"}
                Job Description:
{job_description}
                ------JOB END--------
                """
            else:
                combined_input_for_llm += f"""

                ------ARTICLE START------
                Article ID: {article_id}
                URL: {url}
                Content: {title}
                ------ARTICLE END--------
                """
        #=================LLM PROMPT==================
        prompt = get_hiring_extraction_prompt(combined_input_for_llm)

        #=============EXTRACT JSON FROM RESULT===============
        try:
            response = await rate_limited_gemini_call(prompt)
            response_data = response.text
            extracted_json_data = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model's JSON response: {e.msg}")
            return return_data
        except Exception as e:
            logger.error(f"Error during Gemini API call")
            return return_data

        #===============ADD URL & ID BACK IN RESULT=================
        num_articles = len(extracted_json_data.get("article_id"))

        #Ensure article_link exists in extracted_json_data
        if "article_link" not in extracted_json_data:
            extracted_json_data["article_link"] = [""] * num_articles
        #Extend article_link if it's less than the number of articles
        elif len(extracted_json_data["article_link"]) < num_articles:
            extracted_json_data["article_link"].extend([""] * num_articles-len(extracted_json_data["article_link"]))

        for i in range(num_articles):
            article_id = extracted_json_data["article_id"][i]

            original_data = id_to_data_map.get(article_id, {})
            extracted_json_data["article_link"][i] = original_data.get("url", "")

        logger.info("AI information extraction is done")
        return extracted_json_data

    except Exception as e:
        logger.error(f"AI information extraction failed: {str(e)}")
        return return_data

#===============REGROUP THE BATCHES================
async def finalize_ai_extraction(ids_urls_titles: Dict[str, List[str]])->Dict[str, List[Any]]:
    final_results = {}
    try:
        logger.info("Finalizing AI extraction...")
        list_of_batches = split_into_batches(ids_urls_titles, BATCH_SIZE)
        tasks = [safe_process_hiring_data_batch(batch) for batch in list_of_batches]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            for key, val in result.items():
                if key not in final_results:
                    final_results[key] = val
                else:
                    if isinstance(final_results[key], list) and isinstance(val, list):
                        final_results[key].extend(val)

        logger.info("AI extraction done")
        return final_results

    except Exception as e:
        logger.error(f"Failed to regroup the batches: {str(e)}")
        return final_results

async def fake_prompt(n):
    start = time.perf_counter()
    await rate_limited_gemini_call(f"Prompt {n}")
    end = time.perf_counter()
    print(f"Task {n} finished in {end - start:.2f}s")

async def main():
    tasks = [fake_prompt(i) for i in range(5)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())