import json
import logging
import asyncio
import os
import time
from typing import Optional, Dict, Any

import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from dotenv import load_dotenv
from google.auth import default
from google.auth.transport.requests import Request

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
    raise ValueError("GCP_PROJECT_ID not set in env variables")

REGION = os.getenv("GCP_REGION", "us-central1")
MODEL_NAME = "gemini-2.0-flash"

VERTEX_ENDPOINT = (
    f"https://{REGION}-aiplatform.googleapis.com/v1/"
    f"projects/{PROJECT_ID}/locations/{REGION}/"
    f"publishers/google/models/{MODEL_NAME}:generateContent"
)

# -------------------------------------------------------------------
# Concurrency & Rate Limiting
# -------------------------------------------------------------------
MAX_CONCURRENT_REQUEST = 1
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

RATE_LIMIT_SECONDS = 6
gemini_lock = asyncio.Lock()
last_call = 0

# -------------------------------------------------------------------
# Auth Helper
# -------------------------------------------------------------------
def get_access_token() -> str:
    """Gets a fresh access token for Google Cloud."""
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token

# -------------------------------------------------------------------
# Retry Logic
# -------------------------------------------------------------------
def retry_if_resource_exhausted(exception: BaseException) -> bool:
    """Returns True if the exception is a quota/resource exception."""
    msg = str(exception).lower()
    return "429" in msg or "quota" in msg or "limit" in msg or "503" in msg

def log_before_retry(retry_state: RetryCallState):
    logger.info(f"Retrying Gemini API call... attempt #{retry_state.attempt_number}")

def log_after(retry_state: RetryCallState):
    logger.info(f"Attempt #{retry_state.attempt_number} completed")

def log_failure(retry_state: RetryCallState):
    logger.error("Gemini API failed after retries.")
    return None

# -------------------------------------------------------------------
# Core API Call
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
async def _call_gemini_api_internal(prompt: str) -> str:
    """Call Vertex AI Gemini with retries and timeout."""
    logger.info("Attempting Vertex AI Gemini API call...")

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json"
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(VERTEX_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    logger.info("Gemini API call successful.")
    return data["candidates"][0]["content"]["parts"][0]["text"]

# -------------------------------------------------------------------
# Rate-limited Wrapper
# -------------------------------------------------------------------
async def call_gemini_api(prompt: str) -> Optional[Any]:
    """
    Public interface for calling Gemini API. 
    Handles rate limiting and concurrency.
    """
    global last_call
    
    async with semaphore:
        async with gemini_lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - last_call
            if elapsed < RATE_LIMIT_SECONDS:
                sleep_time = RATE_LIMIT_SECONDS - elapsed
                logger.info(f"Rate limiting in effect, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
            last_call = asyncio.get_running_loop().time()
            
        try:
            # We return a mock response object to maintain compatibility with outreach.py
            text = await _call_gemini_api_internal(prompt)
            
            # Create a simple class to mimic the SDK response structure
            class MockResponse:
                def __init__(self, text):
                    class Part:
                        def __init__(self, text):
                            self.text = text
                    class Content:
                        def __init__(self, text):
                            self.parts = [Part(text)]
                    class Candidate:
                        def __init__(self, text):
                            self.content = Content(text)
                    self.candidates = [Candidate(text)]
            
            return MockResponse(text)
        except Exception as e:
            logger.error(f"Gemini API call for email generation failed: {str(e)}")
            raise

# -------------------------------------------------------------------
# Standalone Test
# -------------------------------------------------------------------
if __name__ == "__main__":
    from utils.prompts.email_generation_prompt import get_email_generation_prompt
    
    async def main():
        desc = "Enquire AI is a technology company based in Washington DC that has developed the world's first agentic research platform. This platform combines expert human judgment with the efficiency of large language models to provide real-time, verifiable insights across business, finance, and policy sectors. Enquire AI aims to enhance how organizations access and utilize expert knowledge, making them more knowledge-efficient for improved business outcomes. The platform features a multi-agent system that synthesizes expert input and produces decision-ready outputs quickly, often in hours. It allows users to engage in real-time dialogues with vetted subject-matter experts, streamlining the research process. Enquire AI also emphasizes compliance and security, ensuring that its services are reliable for various industries. The company serves a diverse clientele, including business leaders, researchers, and analysts, all seeking faster and more accurate answers to complex questions."
        fname = "Cenk"
        cname = "Enquire AI" 
        ttype = "funding"
        fround = "latest"
        seq_no = 1
        
        prompt = get_email_generation_prompt(desc, fname, cname, ttype, seq_no, fround)
        
        try:
            response = await call_gemini_api(prompt)
            if not response:
                print("No response from API")
                return
                
            text = response.candidates[0].content.parts[0].text
            email_json = json.loads(text)
            
            final_subject = email_json["subject"].format(
                first_name=fname,
                company_name=cname,
                company_description=desc,
                funding_round=fround if ttype == "funding" else None
            )
            
            print(f"\nSUBJECT: {final_subject}")
            print(f"CONTENT: {email_json['content']}")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            
    asyncio.run(main())