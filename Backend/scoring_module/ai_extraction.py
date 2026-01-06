#This file queries an LLM to figure out whether a company is looking
#for higher or lower level work

import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict
from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt
from utils.prompts.work_category_prompt import get_work_category
from utils.ai_keywords import marking_scheme_keywords

#Configure logging 
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#Gemini Client
load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found")

client = genai.Client(api_key=GEMINI_API_KEY)
# Using gemini-2.0-flash as it is more stable in current tests
MODEL_NAME = 'gemini-2.0-flash'

#Rate limiting settings
REQUEST_INTERVAL = 6
gemini_lock = asyncio.Lock()
last_call = 0
semaphore = asyncio.Semaphore(1) 

def retry_if_resource_exhausted(exception: BaseException) -> bool:
    """Returns True if the exception is a quota/resource exception."""
    err_str = str(exception).lower()
    return "429" in err_str or "quota" in err_str or "limit" in err_str

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_resource_exhausted,
    reraise=True
)
async def _call_gemini_api_with_retry(prompt: str):
    logger.info("Attempting Gemini API call for work category...")
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            )
        ),
        timeout=30.0
    )
    logger.info("Gemini API call for work category successful.")
    return response

async def extract_work_category(prompt: str)->Dict[str,str]:
    global last_call

    logger.info("Extracting work category from LLM...")
    async with semaphore:
        async with gemini_lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - last_call
            if elapsed < REQUEST_INTERVAL:
                await asyncio.sleep(REQUEST_INTERVAL - elapsed)
            last_call = asyncio.get_running_loop().time()

        try:
            response = await _call_gemini_api_with_retry(prompt)
            raw_text = response.text
            parsed = json.loads(raw_text) #convert to dict
            return parsed

        except Exception as e:
            logger.error(f"Gemini API call for work category failed: {str(e)}")
            return {}


if __name__ == "__main__":
    keywords = [
    "connected lifecycle management",
    "application lifecycle management",
    "iec 62304",
    "medical devices",
    "fda",
    "quality management system",
    "iso 13485",
    "iso 14971",
    "21 cfr part 11",
    "traceability",
    "risk management",
    "requirements management",
    "vmodel",
    "software development",
    "ai/ml model documentation",
    "vulnerability management",
    "regulatory standards for medical ai",
    "regulatory process integration",
    "ai/ml lifecycle compliance",
    "healthcare technology",
    "devtools integration",
    "medical device quality management",
    "regulatory requirements",
    "regulatory documentation",
    "regulatory standards in healthcare",
    "ai/ml model monitoring",
    "regulatory audit support",
    "ai governance in healthcare",
    "ai/ml model traceability",
    "regulatory quality assurance",
    "software validation",
    "automated test traceability",
    "regulatory audit readiness",
    "automated risk assessment for ai",
    "ai model validation",
    "automated regulatory documentation",
    "regulatory compliance software",
    "regulatory compliance",
    "regulatory submission readiness",
    "medical device software development",
    "ai/ml model risk control",
    "regulatory standards compliance",
    "ai/ml software development",
    "regulatory compliance in digital health",
    "compliance automation",
    "regulatory standards",
    "regulatory documentation automation",
    "regulatory process enforcement",
    "regulatory audit trail automation",
    "regulatory standards for samd",
    "regulatory compliance tools",
    "ai/ml in regulated environments",
    "software development automation",
    "regulatory workflows",
    "software development lifecycle",
    "medical device software",
    "regulatory compliance for ai",
    "samd risk management",
    "ai/ml compliance monitoring",
    "regulatory approval for samd",
    "regulatory risk assessment",
    "regulatory documentation tools",
    "system of systems architecture",
    "regulatory approval process for ai",
    "ai/ml in medical devices",
    "samd development",
    "software validation tools",
    "regulatory approval automation",
    "regulatory compliance monitoring",
    "regulatory compliance platform",
    "regulatory compliance for software updates",
    "regulatory risk control",
    "regulatory process automation",
    "regulatory risk management",
    "regulatory compliance for connected devices",
    "automated testing",
    "regulatory documentation generation",
    "ai/ml model validation process",
    "regulatory standards adherence",
    "qms enforcement",
    "ai/ml validation",
    "component reuse",
    "fda compliance",
    "regulatory documentation management",
    "regulatory documentation review",
    "regulatory process control",
    "automated ai model validation",
    "automated compliance workflows",
    "software lifecycle management",
    "automated ai validation workflows",
    "regulatory lifecycle management",
    "ai/ml validation framework",
    "open-source sbom",
    "regulatory audit trail",
    "automated documentation",
    "ai/ml model validation tools",
    "ai/ml model lifecycle management",
    "b2b",
    "services",
    "research and development in the physical, engineering, and life sciences",
    "hospital & health care",
    "information technology & services",
    "medical"
    ]
    name = "Adept"
    prompt = get_work_category(name, keywords, marking_scheme_keywords)

    async def main():
        result = await extract_work_category(prompt)
        logger.info(result)

    asyncio.run(main())