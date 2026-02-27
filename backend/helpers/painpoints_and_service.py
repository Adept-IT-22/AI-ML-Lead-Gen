# Find a company's pain points and service based on their description
import asyncio
import logging
from typing import Dict, List
from utils.safety_checker import safe_dict, safe_list
from outreach_module.ai_email_generation import call_gemini_api

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_painpoints_and_service(enrichment_storage_queue: asyncio.Queue)->List[Dict[str, str]]:
    if enrichment_storage_queue.empty():
        return []

    # Get enrichment data
    enrichment_data = await enrichment_storage_queue.get()

    #Get short_descirption from bulk_enriched_orgs
    bulk_enriched_orgs = enrichment_data.get('bulk_enriched_orgs') 

    bulk_enriched_organizations = [
        org
        for bulk_list in safe_list(bulk_enriched_orgs)
        for org in safe_list(safe_dict(bulk_list[0]).get("organizations")) if bulk_list
    ]

    short_description = ""
    if bulk_enriched_organizations:
        for bulk_enriched_org in bulk_enriched_organizations:
            short_description = bulk_enriched_org.get("short_description", "")
            if short_description:
                break

    # Get the painpoints and service using an llm
    painpoints_and_service = await ai_generated_painpoints_and_service(short_description)

    return painpoints_and_service
    
# AI call to fetch painpoints and service
async def ai_generated_painpoints_and_service(company_description: str)->Dict[str, str]:
    prompt = """
        Take the following prompt and return the following data:
        1. A list of not more than 3 most urgent pain points that the company has/might have
        2. Which service they're most likely to need between 'ai/ml services' and 'software development services'. 
        If it's ai/ml return 'ai/ml', if it's software development return 'software development international'

        {prompt}

        Important! Return the data in json format with keys being painpoints and service e.g.
        {
            'painpoints': ['scaling the software team', 'high cost of developing software'],
            'service': 'software development international'
        }
    """

    response = await call_gemini_api(prompt)
    if not response:
        print("No response from API")
        return {}
        
    text = response.candidates[0].content.parts[0].text

    try:
        # Improved parsing to handle potential markdown code blocks in Gemini response
        clean_text = text.replace("```json", "").replace("```", "").strip()
        import json
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"Failed to parse AI response: {text}. Error: {e}")
        return {"error": "Invalid JSON response", "raw_text": text}


if __name__ == "__main__":
    async def main():
        enriched_data = {
            "single_enriched_orgs": [{}],
            "bulk_enriched_orgs": [[{
                "organizations": [{
                    "name": "Darwin AI",
                    "short_description": "Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance their sales strategies through AI-driven insights."
                    }]
            }]]
        }

        enrichment_storage_queue = asyncio.Queue()
        #await enrichment_storage_queue.put(enriched_data)
        x = await get_painpoints_and_service(enrichment_storage_queue)
        print(x)

    asyncio.run(main())

    
