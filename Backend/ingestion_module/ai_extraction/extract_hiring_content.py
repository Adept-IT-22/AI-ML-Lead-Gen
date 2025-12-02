import os
import time
import json
import logging
import traceback
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict, Union
import google.generativeai as genai
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

# Initialize model - handle different versions of google-generativeai
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Try to use GenerativeModel (newer API)
    if hasattr(genai, 'GenerativeModel'):
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
        )
        USE_NEW_API = True
    else:
        # Fallback for older versions (0.1.0rc1) - use generate_text or chat_async
        logger.info("Using older google-generativeai API (generate_text)")
        model = None
        USE_NEW_API = False
        # For older API, we'll use generate_text directly
        MODEL_NAME = "gemini-2.5-flash"
except Exception as e:
    logger.error(f"Error initializing Gemini model: {str(e)}")
    model = None
    USE_NEW_API = False
    MODEL_NAME = None

BATCH_SIZE = 5 #How many jobs we want to feed the LLM at a time

#=============REQUEST CONCURRENCY==============
MAX_CONCURRENT_REQUEST = 1 #How many API request we can send the LLM at a time
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

#========================HELPER CLASSES=============================
class MockResponse:
    """Mock response object for older API compatibility."""
    def __init__(self, text):
        self.text = text

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
#Check if exception is a ResourceExhaustedException or TimeoutError
def retry_if_resource_exhausted_or_timeout(exception: BaseException) -> bool:
    """Returns True if the exception is a ResourceExhausted or TimeoutError exception."""
    return isinstance(exception, (ResourceExhausted, asyncio.TimeoutError, TimeoutError))


def log_before_retry(retry_state: RetryCallState):
    if retry_state.attempt_number > 1:
        logger.info(f"Retrying Gemini API call... attempt #{retry_state.attempt_number}")

def log_after(retry_state: RetryCallState):
    # Only log successful retries, not every attempt
    if retry_state.attempt_number > 1:
        logger.info(f"Attempt #{retry_state.attempt_number} completed successfully")

def log_failure():
    logger.error("Gemini API failed after retries.")
    return

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_resource_exhausted_or_timeout,
    reraise=True,
    before=log_before_retry,
    after=log_after,
    retry_error_callback=log_failure
)
async def _call_gemini_api_with_retry(prompt: str):
    """Internal function to call Gemini API with retry logic."""
    # Only log on first attempt, retries are logged separately
    # logger.debug("Attempting Gemini API call for hiring...")
    
    # Calculate timeout based on prompt length (longer prompts need more time)
    # Base timeout of 60 seconds, add 1 second per 1000 characters
    prompt_length = len(prompt)
    timeout = 60.0 + (prompt_length / 1000)
    
    try:
        if USE_NEW_API and model:
            # New API with GenerativeModel
            from google.generativeai import types
            response = await asyncio.wait_for(
                model.generate_content_async(
                    contents=prompt,
                    generation_config=types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.5,
                    )
                ),
                timeout=timeout
            )
        else:
            # Older API (0.1.0rc1) - use generate_text
            if not MODEL_NAME:
                raise ValueError("Gemini model not properly initialized")
            
            # Use generate_text for older API
            # generate_text returns a result object with .result attribute
            # Use to_thread if available (Python 3.9+), otherwise use executor (Python 3.8)
            if hasattr(asyncio, 'to_thread'):
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        genai.generate_text,
                        model=MODEL_NAME,
                        prompt=prompt,
                        temperature=0.5,
                    ),
                    timeout=timeout
                )
            else:
                # Fallback for Python 3.8
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: genai.generate_text(
                            model=MODEL_NAME,
                            prompt=prompt,
                            temperature=0.5,
                        )
                    ),
                    timeout=timeout
                )
            
            # Extract text from result object
            response_text = result.result if hasattr(result, 'result') else str(result)
            response = MockResponse(response_text)
        
        # logger.debug("Gemini API for hiring call successful.")
        return response
    except asyncio.TimeoutError as e:
        error_msg = f"Request timed out after {timeout:.1f}s (prompt length: {prompt_length} chars)"
        logger.error(f"Gemini API call for hiring failed: TimeoutError - {error_msg}")
        # Re-raise as TimeoutError so retry logic can catch it
        raise asyncio.TimeoutError() from e
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        error_type = type(e).__name__
        logger.error(f"Gemini API call for hiring failed: {error_type} - {error_msg}")
        logger.debug(f"Full traceback:\n{traceback.format_exc()}")
        raise

#=======================PROCESS EACH BATCH=========================
async def process_hiring_data_batch(batch: Dict[str, List[Union[str, int]]])->Dict[str, List[Any]]:
    # logger.debug("AI hiring information extraction beginning...")

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
            logger.debug(f"Response text (first 500 chars): {response_data[:500] if 'response_data' in locals() else 'N/A'}")
            return return_data
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            error_type = type(e).__name__
            logger.error(f"Error during Gemini API call: {error_type} - {error_msg}")
            logger.debug(f"Full traceback:\n{traceback.format_exc()}")
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

        # logger.debug("AI information extraction is done")
        return extracted_json_data

    except Exception as e:
        logger.error(f"AI information extraction failed: {str(e)}")
        return return_data

#===============REGROUP THE BATCHES================
async def finalize_ai_extraction(ids_urls_titles: Dict[str, List[str]])->Dict[str, List[Any]]:
    final_results = {}
    try:
        logger.info("Finalizing AI extraction...")
        total_items = len(ids_urls_titles["ids"])
        list_of_batches = split_into_batches(ids_urls_titles, BATCH_SIZE)
        num_batches = len(list_of_batches)
        logger.info(f"Processing {total_items} items in {num_batches} batches (batch size: {BATCH_SIZE})")
        tasks = [safe_process_hiring_data_batch(batch) for batch in list_of_batches]
        # Use return_exceptions=True to continue processing even if some batches fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling exceptions
        successful_batches = 0
        failed_batches = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_batches += 1
                error_type = type(result).__name__
                logger.error(f"Batch {i + 1} failed with {error_type}: {str(result)}")
                continue
            
            successful_batches += 1
            for key, val in result.items():
                if key not in final_results:
                    final_results[key] = val
                else:
                    if isinstance(final_results[key], list) and isinstance(val, list):
                        final_results[key].extend(val)
        
        if failed_batches > 0:
            logger.warning(f"Completed with {successful_batches} successful batches and {failed_batches} failed batches")

        # Log summary of extracted data
        num_extracted = len(final_results.get("article_id", []))
        success_rate = (num_extracted / total_items * 100) if total_items > 0 else 0
        logger.info("")
        logger.info(f"AI extraction completed: {num_extracted}/{total_items} items extracted ({success_rate:.1f}% success rate)")
        if num_extracted > 0:
            logger.info(f"Result contains {len(final_results)} data fields")
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