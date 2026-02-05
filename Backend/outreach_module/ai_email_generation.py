import json
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
    logger.info("Attempting Gemini API call for email generation...")
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
        logger.info("Gemini API call for email generation.")
        return response
    except Exception as e:
        logger.error(f"Gemini API call for email generation failed: {str(e)}")
        raise 


if __name__ == "__main__":
    from utils.prompts.email_generation_prompt import get_email_generation_prompt
    async def main():
        desc = "Enquire AI is a technology company based in Washington DC that has developed the world's first agentic research platform. This platform combines expert human judgment with the efficiency of large language models to provide real-time, verifiable insights across business, finance, and policy sectors. Enquire AI aims to enhance how organizations access and utilize expert knowledge, making them more knowledge-efficient for improved business outcomes. The platform features a multi-agent system that synthesizes expert input and produces decision-ready outputs quickly, often in hours. It allows users to engage in real-time dialogues with vetted subject-matter experts, streamlining the research process. Enquire AI also emphasizes compliance and security, ensuring that its services are reliable for various industries. The company serves a diverse clientele, including business leaders, researchers, and analysts, all seeking faster and more accurate answers to complex questions."
        fname = "Cenk"
        cname = "Enquire AI" 
        ttype = "funding"
        fround = "latest"
        seq_no = 4
        prompt = get_email_generation_prompt(desc, fname, cname, ttype, seq_no, fround)
        try:
            response = await call_gemini_api(prompt)
            print(response)
            x = response.candidates[0].content.parts[0].text
            
            email_json = json.loads(x)
        except json.JSONDecodeError:
            logger.error("Invalid json from llm")
            return True
            
        email_subject=email_json["subject"]
        email_content=email_json["content"]

        final_subject = email_subject.format(
            first_name=fname if fname else None,
            company_name=cname if cname else None,
            company_description=desc if desc else None,
            funding_round=fround if ttype == "funding" and fround else None
        )

        final_content = email_content.format(
            first_name=fname if fname else None,
            company_name=cname if cname else None,
            company_description=desc if desc else None,
            funding_round=fround if ttype == "funding" and fround else None
        )

        print(final_subject)
        print(final_content)
            
    asyncio.run(main())