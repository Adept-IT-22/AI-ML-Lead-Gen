import os
import time
import json
import logging
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv
from typing import List, Any, Dict
import google.generativeai as genai
from google.generativeai import types
from google.api_core.exceptions import ResourceExhausted

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

"""
The functions below are to be used by the funding, hiring and events code. 
Their job is to take in and return data in the below format. In between
that, they will batch the input data up, feed it to an LLM which will turn the
paragraphs into meaningful information for us.
{
    "urls": ["link1", "link2", "link3"],
    "paragraphs": ["article_text1", "article_text2", "article_text2"]
}
"""

BATCH_SIZE = 4 #How many articles we want to feed the llm at a time
MAX_CONCURRENT_REQUEST = 4 #How many API request we can send the llm at a time
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

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
    logger.info(json.dumps(result, indent=2))
    return result
    
#===============================HANDLE RETRIES====================================
#Check if exception is a ResourceExhaustedException
def retry_if_resource_exhausted(exception: BaseException) -> bool:
    """Returns True if the exception is a ResourceExhausted exception."""
    return isinstance(exception, ResourceExhausted)

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60), 
    stop=stop_after_attempt(5), 
    retry=retry_if_resource_exhausted,
    reraise=True
)
async def _call_gemini_api_with_retry(prompt: str) -> types.GenerateContentResponse:
    """Internal function to call Gemini API with retry logic."""
    logger.info("Attempting Gemini API call...")
    response = await model.generate_content_async(
        contents=prompt,
        generation_config=types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.5,
        )
    )
    logger.info("Gemini API call successful.")
    return response

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
        prompt = f"""
        You are an expert trained to extract funding news from news articles.
        Analyze the following group of news articles. For each article, extract the following information:
        - Article Title
        - Date of Article (format as YYYY-MM-DD if possible)
        - Company Name
        - Company City
        - Company Country
        - Company Decision Makers (as a list of strings. Include names of all identifiable decision makers for the company that's raising money.)
        - Funding Round (e.g., Seed, Series A, Series B, Venture, Private Equity, Debt, Grant, Convertible Note, Bridge, IPO, Acquisition, etc. If not explicitly mentioned, infer based on context or leave empty string if no clear indication.)
        - Amount Raised (e.g., $10M, €5M, £2.5M. Extract the numerical value and currency symbol.)
        - Currency (e.g., USD, EUR, GBP. Infer from amount raised or context.)
        - Investor Companies (as a list of strings. Include names of all identifiable investor companies.)
        - Investor People (as a list of strings. Include names of all identifiable investor people associated with the above mentioned companies.)
        - Tags (as a list of strings, relevant to the company/funding event.)
        - Original Article ID (the 'Article_ID' provided for each article in the input. This is crucial for matching results.)

        If any information on a particular field is not present or cannot be confidently extracted, return an empty string "" for string fields or an empty list [] for list fields. Do not make up information.

        **IMPORTANT:** Return a dictionary in the structure of arrays format.

        Example of desired output structure for multiple articles:
        {
            {
                "article_id": [0, 1],
                "article_title": ["Tech Startup A Secures $5M Seed Funding", "Green Energy Co. B Closes Series B Round for €10 Million"],
                "article_date": ["2024-07-25", "2025-04-12"],
                "company_name": ["Tech Startup A", "Tech Startup B"],
                "company_city": ["San Francisco", "Berlin"],
                "company_country": ["America", "Germany"],
                "company_decision_makers": [["John Doe"],["Jane Doe", "John Smith"]],
                "funding_round": ["Seed", "Series A"],
                "amount_raised": ["$5M", "$10M"],
                "currency": ["USD", "USD"],
                "investor_companies": [["VC Firm Alpha", "Angel Investor Beta"], ["GreenTech Investments"]],
                "investor_people": [["John Doe", "John Smith"], ["Jane Doe"]],
                "tags": [["tech", "startup", "funding", "SaaS", "innovation"], ["energy", "sustainability"]]
            }
        }

        Articles Text:
        \"\"\"
        {combined_input_for_llm}
        \"\"\"
        """

        #=============EXTRACT JSON FROM RESULT===============
        try:
            response = await _call_gemini_api_with_retry(prompt)
            response_data = response.text
            extracted_json_data = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model's JSON response: {e.msg}")
            logger.info("The response data is:")
            logger.info(json.dumps(response_data, indent=2))
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

        final_results = {}
        for result in results:
            for key, val in result.items():
                if key not in final_results:
                    final_results[key] = val
                else:
                    final_results[key].extend(val)
        logger.info("AI extraction done")
        return final_results

    except Exception as e:
        logger.error(f"Failed to regroup the batches: {str(e)}")