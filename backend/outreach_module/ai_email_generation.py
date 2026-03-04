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
    
    async def test_email_generation(desc, fname, cname, ttype, seq_no, fround=None, hiring_area=None, painpoints=None):
        print(f"\n--- TESTING {ttype.upper()} EXAMPLE ---")
        prompt = get_email_generation_prompt(
            company_description=desc,
            first_name=fname,
            company_name=cname,
            trigger_type=ttype,
            sequence_number=seq_no,
            funding_round=fround,
            hiring_area=hiring_area,
            painpoints=painpoints
        )
        
        try:
            response = await call_gemini_api(prompt)
            if not response:
                print("No response from API")
                return
                
            text = response.candidates[0].content.parts[0].text
            email_json = json.loads(text)
            
            # Safety net: format both subject and content with provided variables
            format_dict = {
                "first_name": fname,
                "company_name": cname,
                "company_description": desc,
                "funding_round": fround if fround else "",
                "hiring_area": hiring_area if hiring_area else ""
            }
            
            final_subject = email_json["subject"].format(**format_dict)
            final_content = email_json["content"].format(**format_dict)
            
            print(f"SUBJECT: {final_subject}")
            print(f"CONTENT: {final_content}")
            
        except Exception as e:
            logger.error(f"Test failed for {ttype}: {str(e)}")

    async def main():
        # Example 1: Funding
        desc_funding = "ManageMy is a SaaS technology company based in Charlotte, North Carolina, founded in 2018. The company specializes in an AI-driven digital platform designed for insurance carriers. This platform helps streamline various processes such as buying, underwriting, servicing, and claims, while also driving sales growth and enhancing customer experiences without the need to overhaul existing legacy systems. One of the key offerings is XPerience Studio, a no-code API-based solution that allows carriers to quickly configure workflows, forms, and digital journeys across multiple platforms. The digital front-end platform supports the entire policy lifecycle, including quoting, onboarding, and claims management. Additionally, ManageMy provides integrated marketing services through MyCustomer, which focuses on data-driven campaigns for upselling and retention. The company leverages a team with extensive insurance expertise, emphasizing cybersecurity and regulatory compliance to support its clients effectively."
        fname = "Chris"
        cname = "ManageMy" 
        ttype_funding = "funding"
        fround = "latest"
        seq_no = 1
        painpoints = ['insurers are under growing pressure to improve speed, accuracy, and customer experience while increasing sales and reducing costs', 'insurance industry has struggled to modernise its business models']
        
        await test_email_generation(desc_funding, fname, cname, ttype_funding, seq_no, fround=fround, painpoints=painpoints)

        # Example 2: Hiring
        desc_hiring = "Looking for a partner that can help take your Web2/Web3, Mobile, Blockchain or AI product to the next level? QIT Software is here for you. QIT Software is a software development company based in Plano, Texas. We specialize in crafting bespoke web and mobile solutions, as well as offering dedicated teams and R&D services for Web2/Web3, Mobile, Blockchain, AI and other products. Our team of top-notch engineers and innovators are dedicated to staying ahead of the curve, using the latest tools and technologies to deliver cutting-edge solutions that meet your unique needs and maximize revenue. From AI and machine learning to blockchain and beyond, we're committed to pushing the boundaries of what's possible. With our passion for innovation and commitment to excellence, we'll work with you every step of the way to bring your vision to life. We offer a full suite of outstaffing services and help global businesses scale their engineering teams via IT Staff Augmentation, Dedicated Team and Time & Material cooperation models. 👾 Tech stack we master: React, Vue.js, Angular, TypeScript, JavaScript, Java, .NET, Solidity, Blockchain, PHP, Node.js, Python, iOS, Android, React Native, Ionic, Flutter, Swift, Kotlin, Xamarin, C++, GCP, AWS, Azure, PostgreSQL, MySQL and others. ⚡️ By partnering with QIT Software you get: - a sufficiently shortened onboarding time for new members; - an outstanding cost-quality ratio; - developers who exclusively work for you, regardless of the project length - employees while we handle all the paperwork and cover all the costs; - simplified tax system to the reduced staff; - stress release. We handle all the paperwork and cover all the desk costs; - transparent direct line of communication; - full development process supervision by being in touch with your remote team. 🤝🏼 Drop us a line to discuss your project."
        fname_hiring = "Yegor"
        cname_hiring = "QIT Software"
        ttype_hiring = "hiring"
        hiring_area = "Data Engineer"
        seq_no_hiring = 1
        painpoints_hiring = ["enhancing productivity","innovation"]

        await test_email_generation(desc_hiring, fname_hiring, cname_hiring, ttype_hiring, seq_no_hiring, hiring_area=hiring_area, painpoints=painpoints_hiring)
            
    asyncio.run(main())