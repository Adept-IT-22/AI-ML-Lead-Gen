#import os
#import time
#import json
#import logging
#import asyncio
#from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
#from dotenv import load_dotenv
#from typing import List, Any, Dict
#from google import genai
#from google.genai import types
#from utils.prompts.funding_prompt import get_funding_extraction_prompt

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#logger = logging.getLogger(__name__)

##Import env variables
#load_dotenv(verbose=True, override=True)

##Gemini Client
#GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
#if not GEMINI_API_KEY:
    #raise ValueError("Gemini API Key not found in env variables")

#client = genai.Client(api_key=GEMINI_API_KEY)
#MODEL_NAME = "gemini-2.0-flash" 

#BATCH_SIZE = 4 #How many jobs we want to feed the llm at a time

##================REQUEST CONCURRENCY============
#MAX_CONCURRENT_REQUEST = 1 #How many API request we can send the llm at a time
#semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

##==============API RATE LIMITS===============
#RATE_LIMIT_SECONDS = 6
#gemini_lock = asyncio.Lock()
#last_call = 0   

#async def rate_limited_gemini_call(prompt: str):
    #global last_call
    #async with gemini_lock:
        #now = asyncio.get_running_loop().time()
        #elapsed = now - last_call

        #if elapsed < RATE_LIMIT_SECONDS:
            #sleep_time = RATE_LIMIT_SECONDS - elapsed
            #logger.info(f"Rate limiting in effect, sleeping for {sleep_time:.2f}s")
            #await asyncio.sleep(sleep_time)

        #last_call = asyncio.get_running_loop().time()  # Update AFTER waiting
        #return await _call_gemini_api_with_retry(prompt)

##Wrapper around process_article_batch to enforce the semaphore
#async def safe_process_articles_batch(batch: Dict[str, List[Any]]):
    #async with semaphore:
        #return await process_articles_batch(batch)

##======================SPLIT DATA INTO BATCHES===========================
#def split_into_batches(links_and_paragraphs: Dict[str, List[str]], BATCH_SIZE)->List[Dict[str, List[Any]]]:
    #logger.info("Splitting funding data into batches...")
    #total_articles = len(links_and_paragraphs["urls"])
    #result = []
    #for i in range(0, total_articles, BATCH_SIZE):
        #result.append(
            #{
                #"urls": links_and_paragraphs["urls"][i:i+BATCH_SIZE],
                #"paragraphs": links_and_paragraphs["paragraphs"][i:i+BATCH_SIZE]
            #}
        #)
    #logger.info("Splitting funding data into batches done")
    #return result
    
##Check if exception is related to rate limits/quota
#def retry_if_resource_exhausted(exception: BaseException) -> bool:
    #"""Returns True if the exception is a quota/resource exception."""
    #err_str = str(exception).lower()
    #return "429" in err_str or "quota" in err_str or "limit" in err_str

#def log_before_retry(retry_state: RetryCallState):
    #logger.info(f"Retrying Gemini API call... attempt #{retry_state.attempt_number}")

#def log_after(retry_state: RetryCallState):
    #logger.info(f"Attempt #{retry_state.attempt_number} done")

#def log_failure():
    #logger.error("Gemini API failed after retries.")
    #return

#@retry(
    #wait=wait_exponential(multiplier=1, min=4, max=60),
    #stop=stop_after_attempt(5),
    #retry=retry_if_resource_exhausted,
    #reraise=True,
    #before=log_before_retry,
    #after=log_after,
    #retry_error_callback=log_failure
#)
##Internal function to call Gemini API with retry logic.
#async def _call_gemini_api_with_retry(prompt: str):
    #logger.info("Attempting Gemini API call for funding...")
    #response = await asyncio.wait_for(
        #client.aio.models.generate_content(
            #model=MODEL_NAME,
            #contents=prompt,
            #config=types.GenerateContentConfig(
                #response_mime_type="application/json",
                #temperature=0,
            #)
        #),
    #timeout=30.0
    #)
    #logger.info("Gemini API call for funding successful.")
    #return response

##=======================PROCESS EACH BATCH=========================
#async def process_articles_batch(batch: Dict[str, List[Any]])->Dict[str, List[Any]]:
    #logger.info("AI funding information extraction beginning...")

    #return_data = {
        #"type": "funding",
        #"title": [],
        #"link": [],
        #"article_date": [],
        #"company_name": [],
        #"city": [],
        #"country": [],
        #"company_decision_makers": [],
        #"funding_round": [],
        #"amount_raised": [],
        #"currency": [],
        #"investor_companies": [],
        #"investor_people": [],
        #"tags": []
    #}

    #try:
        #id_url_map: Dict[int, str] = {} #Maps every url to an ID
        #combined_input_for_llm = ""


        #for id, (url, paragraphs) in enumerate(zip(batch["urls"], batch["paragraphs"])):
            #id_url_map[id] = url    
            #combined_input_for_llm += f"""

            #------ARTICLE START------
            #Article: {id},\n
            #URL: {url},\n
            #Content: {paragraphs}\n
            #------ARTICLE END--------
            #"""

        ##=================LLM PROMPT==================
        #prompt = get_funding_extraction_prompt(combined_input_for_llm)

        ##=============EXTRACT JSON FROM RESULT===============
        #try:
            #response = await _call_gemini_api_with_retry(prompt)
            #response_data = response.text
            #extracted_json_data = json.loads(response_data)
        #except json.JSONDecodeError as e:
            #logger.error(f"Failed to parse model's JSON response: {e.msg}")
            #return return_data


        ##===============ADD URL BACK IN RESULT=================
        #num_articles = len(extracted_json_data.get("article_id"))

        ##Ensure article_link exists in extracted_json_data
        #if "article_link" not in extracted_json_data:
            #extracted_json_data["article_link"] = [""] * num_articles
        ##Extend article_link if it's less than the number of articles
        #elif len(extracted_json_data["article_link"]) < num_articles:
            #extracted_json_data["article_link"].extend([""] * num_articles-len(extracted_json_data["article_link"]))

        #for i in range(num_articles):
            #original_url = id_url_map[i]
            #extracted_json_data["article_link"][i] = original_url

        #logger.info("AI information extraction is done")
        #return extracted_json_data

    #except Exception as e:
        #logger.error(f"AI information extraction failed: {str(e)}")
        #return return_data

##===============REGROUP THE BATCHES================
#async def finalize_ai_extraction(links_and_paragraphs: Dict[str, List[str]])->Dict[str, List[Any]]:
    #final_results = {}
    #try:
        #logger.info("Finalizing AI extraction...")
        #list_of_batches = split_into_batches(links_and_paragraphs, BATCH_SIZE)
        #tasks = [safe_process_articles_batch(batch) for batch in list_of_batches]
        #await asyncio.sleep(3)
        #results = await asyncio.gather(*tasks)

        ##Add results from each batch into final_results. 
        #for result in results:
            #for key, val in result.items():
                #if key not in final_results:
                    #final_results[key] = val
                #else:
                    #if isinstance(final_results[key], list) and isinstance(val, list):
                        #final_results[key].extend(val)

        #logger.info("AI extraction done")
        #return final_results

    #except Exception as e:
        #logger.error(f"Failed to regroup the batches: {str(e)}")
        #return final_results

#async def fake_prompt(n):
    #"""Simulate multiple Gemini API calls to test rate limiting & concurrency."""
    #start = time.perf_counter()
    #await rate_limited_gemini_call(f"Fake funding prompt {n}")
    #end = time.perf_counter()
    #print(f"Task {n} finished in {end - start:.2f}s")

#async def main():
    ## Launch multiple fake Gemini calls concurrently
    #tasks = [fake_prompt(i) for i in range(5)]
    #await asyncio.gather(*tasks)

#if __name__ == "__main__":
    #asyncio.run(main())
    

import os
import time
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from typing import List, Any, Dict

import httpx
from google.auth import default
from google.auth.transport.requests import Request

from utils.prompts.funding_prompt import get_funding_extraction_prompt

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Environment Variables
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
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

RATE_LIMIT_SECONDS = 6
gemini_lock = asyncio.Lock()
last_call = 0

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
    logger.error("Gemini API failed after retries.")
    return {}

# -------------------------------------------------------------------
# Rate-limited, retried call to Vertex AI Gemini
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
    """Call Vertex AI Gemini with retries."""
    logger.info("Attempting Gemini API call for funding...")

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(VERTEX_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    logger.info("Gemini API call successful.")
    return data["candidates"][0]["content"]["parts"][0]["text"]

# -------------------------------------------------------------------
# Rate-limiting wrapper
# -------------------------------------------------------------------
async def rate_limited_gemini_call(prompt: str):
    global last_call
    async with gemini_lock:
        now = asyncio.get_running_loop().time()
        elapsed = now - last_call
        if elapsed < RATE_LIMIT_SECONDS:
            await asyncio.sleep(RATE_LIMIT_SECONDS - elapsed)
        last_call = asyncio.get_running_loop().time()
    return await _call_gemini_api_with_retry(prompt)

async def safe_process_articles_batch(batch: Dict[str, List[Any]]):
    async with semaphore:
        return await process_articles_batch(batch)

# -------------------------------------------------------------------
# Batch splitting
# -------------------------------------------------------------------
def split_into_batches(links_and_paragraphs: Dict[str, List[str]], batch_size: int) -> List[Dict[str, List[Any]]]:
    total_articles = len(links_and_paragraphs["urls"])
    result = []
    for i in range(0, total_articles, batch_size):
        result.append({
            "urls": links_and_paragraphs["urls"][i:i+batch_size],
            "paragraphs": links_and_paragraphs["paragraphs"][i:i+batch_size]
        })
    return result

# -------------------------------------------------------------------
# Process batch
# -------------------------------------------------------------------
async def process_articles_batch(batch: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    logger.info("AI funding extraction starting...")
    return_data = {
        "type": "funding",
        "title": [], "link": [], "article_date": [], "company_name": [],
        "city": [], "country": [], "company_decision_makers": [],
        "funding_round": [], "amount_raised": [], "currency": [],
        "investor_companies": [], "investor_people": [], "tags": []
    }

    try:
        id_url_map: Dict[int, str] = {}
        combined_input = ""
        for idx, (url, paragraphs) in enumerate(zip(batch["urls"], batch["paragraphs"])):
            id_url_map[idx] = url
            combined_input += f"\n------ARTICLE START------\nArticle: {idx}\nURL: {url}\nContent: {paragraphs}\n------ARTICLE END------\n"

        prompt = get_funding_extraction_prompt(combined_input)
        response_text = await _call_gemini_api_with_retry(prompt)

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
            extracted_json_data["article_link"][i] = id_url_map[i]

        return extracted_json_data

    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        return return_data

# -------------------------------------------------------------------
# Finalize all batches
# -------------------------------------------------------------------
async def finalize_ai_extraction(links_and_paragraphs: Dict[str, List[str]]) -> Dict[str, List[Any]]:
    final_results = {}
    try:
        batches = split_into_batches(links_and_paragraphs, BATCH_SIZE)
        tasks = [safe_process_articles_batch(batch) for batch in batches]
        await asyncio.sleep(3)  # small delay
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
    await rate_limited_gemini_call(f"Fake funding prompt {n}")
    end = time.perf_counter()
    print(f"Task {n} finished in {end - start:.2f}s")

async def main():
    tasks = [fake_prompt(i) for i in range(5)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
