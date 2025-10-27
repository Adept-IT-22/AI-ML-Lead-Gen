import os
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict, Union
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
MAX_CONCURRENT_REQUEST = 10 #How many API request we can send the llm at a time
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
def split_into_batches(ids_urls_titles: Dict[str, List[str]], BATCH_SIZE)->List[Dict[str, List[Any]]]:
    logger.info("Splitting hiring data into batches...")
    total_articles = len(ids_urls_titles["ids"])
    result = []
    for i in range(0, total_articles, BATCH_SIZE):
        result.append(
            {
                "ids": ids_urls_titles["ids"][i:i+BATCH_SIZE],
                "urls": ids_urls_titles["urls"][i:i+BATCH_SIZE],
                "titles": ids_urls_titles["titles"][i:i+BATCH_SIZE]
            }
        )
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
        id_to_data_map: Dict[int, Dict[str, Any]] = {} #Maps every article ID to its url and title
        combined_input_for_llm = ""


        for article_id, url, title in zip(batch["ids"], batch["urls"], batch["titles"]):
            id_to_data_map[article_id] = {"url": url, "title": title}   
            combined_input_for_llm += f"""

            ------ARTICLE START------
            Article: {article_id},\n
            URL: {url},\n
            Content: {title}\n
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