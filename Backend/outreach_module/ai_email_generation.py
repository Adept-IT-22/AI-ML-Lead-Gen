from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
import google.generativeai as genai
from google.generativeai import types
from google.api_core.exceptions import ResourceExhausted
import logging
import asyncio
from dotenv import load_dotenv
import os
from aiolimiter import AsyncLimiter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
async def call_gemini_api(prompt: str) -> types.GenerateContentResponse:
    logger.info("Attempting Gemini API call for funding...")
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                contents=prompt,
                generation_config=types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0,
                )
            ),
        timeout=30.0
        )
        logger.info("Gemini API call for funding successful.")
        return response
    except Exception as e:
        logger.error(f"Gemini API call for funding failed: {str(e)}")
        return 


if __name__ == "__main__":
    from utils.prompts.email_generation_prompt import get_email_generation_prompt
    async def main():
        desc = "Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance their sales strategies through AI-driven insights."
        fname = "mark"
        cname = "adept"
        ttype = "funding"
        fround = "seed"
        prompt = get_email_generation_prompt(desc, fname, cname, ttype, fround)
        result = await call_gemini_api(prompt)
        print(result.text)
    asyncio.run(main())