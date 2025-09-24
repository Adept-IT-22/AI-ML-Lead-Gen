#This file queries an LLM to figure out whether a company is looking
#for higher or lower level work

import os
import json
import asyncio
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types
from utils.prompts.work_category_prompt import get_work_category

#Configure logging 
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#Configure LLM
load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name = 'gemini-2.5-flash'
)

async def extract_work_category(prompt: str):
    logger.info("Extracting work category from LLM...")
    try:
        response = await model.generate_content_async(
            contents=prompt,
            generation_config=types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0,
            )
        )
        logger.info("Gemini API call for work category successful.")
        return response.parts[0] if response.parts[0] else response.parts
    except Exception as e:
        logger.error(f"Gemini API call for work category failed: {str(e)}")
        return 

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
    prompt = get_work_category(keywords)
    prompt = prompt.format(keywords=json.dumps(keywords, indent=2))

    async def main():
        result = await extract_work_category(prompt)
        logger.info(result)

    asyncio.run(main())