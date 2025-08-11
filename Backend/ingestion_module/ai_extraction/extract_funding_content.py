import os
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict
import google.generativeai as genai
from google.generativeai import types
from google.api_core.exceptions import ResourceExhausted
from utils.prompts.funding_prompt import get_funding_extraction_prompt

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

#================REQUEST CONCURRENCY============
MAX_CONCURRENT_REQUEST = 10 #How many API request we can send the llm at a time
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

#==============API RATE LIMITS===============
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
async def safe_process_articles_batch(batch: Dict[str, List[Any]]):
    async with semaphore:
        return await process_articles_batch(batch)

#======================SPLIT DATA INTO BATCHES===========================
def split_into_batches(links_and_paragraphs: Dict[str, List[str]], BATCH_SIZE)->List[Dict[str, List[Any]]]:
    logger.info("Splitting funding data into batches...")
    total_articles = len(links_and_paragraphs["urls"])
    result = []
    for i in range(0, total_articles, BATCH_SIZE):
        result.append(
            {
                "urls": links_and_paragraphs["urls"][i:i+BATCH_SIZE],
                "paragraphs": links_and_paragraphs["paragraphs"][i:i+BATCH_SIZE]
            }
        )
    logger.info("Splitting funding data into batches done")
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
#Internal function to call Gemini API with retry logic.
async def _call_gemini_api_with_retry(prompt: str) -> types.GenerateContentResponse:
    logger.info("Attempting Gemini API call for funding...")
    try:
        response = await model.generate_content_async(
            contents=prompt,
            generation_config=types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.5,
            )
        )
        logger.info("Gemini API call for funding successful.")
        return response
    except Exception as e:
        logger.error(f"Gemini API call for funding failed: {str(e)}")
        return 

#=======================PROCESS EACH BATCH=========================
async def process_articles_batch(batch: Dict[str, List[Any]])->Dict[str, List[Any]]:
    logger.info("AI funding information extraction beginning...")

    return_data = {
        "type": "news",
        "article_title": [],
        "article_link": [],
        "article_date": [],
        "company_name": [],
        "company_city": [],
        "company_country": [],
        "company_decision_makers": [],
        "funding_round": [],
        "amount_raised": [],
        "currency": [],
        "investor_companies": [],
        "investor_people": [],
        "tags": []
    }

    try:
        id_url_map: Dict[int, str] = {} #Maps every url to an ID
        combined_input_for_llm = ""


        for id, (url, paragraphs) in enumerate(zip(batch["urls"], batch["paragraphs"])):
            id_url_map[id] = url    
            combined_input_for_llm += f"""

            ------ARTICLE START------
            Article: {id},\n
            URL: {url},\n
            Content: {paragraphs}\n
            ------ARTICLE END--------
            """

        #=================LLM PROMPT==================
        prompt = get_funding_extraction_prompt(combined_input_for_llm)

        #=============EXTRACT JSON FROM RESULT===============
        try:
            response = await _call_gemini_api_with_retry(prompt)
            response_data = response.text
            extracted_json_data = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model's JSON response: {e.msg}")
            return return_data


        #===============ADD URL BACK IN RESULT=================
        num_articles = len(extracted_json_data.get("article_id"))

        #Ensure article_link exists in extracted_json_data
        if "article_link" not in extracted_json_data:
            extracted_json_data["article_link"] = [""] * num_articles
        #Extend article_link if it's less than the number of articles
        elif len(extracted_json_data["article_link"]) < num_articles:
            extracted_json_data["article_link"].extend([""] * num_articles-len(extracted_json_data["article_link"]))

        for i in range(num_articles):
            original_url = id_url_map[i]
            extracted_json_data["article_link"][i] = original_url

        logger.info("AI information extraction is done")
        return extracted_json_data

    except Exception as e:
        logger.error(f"AI information extraction failed: {str(e)}")
        return return_data

#===============REGROUP THE BATCHES================
async def finalize_ai_extraction(links_and_paragraphs: Dict[str, List[str]])->Dict[str, List[Any]]:
    try:
        logger.info("Finalizing AI extraction...")
        list_of_batches = split_into_batches(links_and_paragraphs, BATCH_SIZE)
        tasks = [safe_process_articles_batch(batch) for batch in list_of_batches]
        results = await asyncio.gather(*tasks)

        #Add results from each batch into final_results. 
        final_results = {}
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