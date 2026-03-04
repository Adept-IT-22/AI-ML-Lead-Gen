# Find a company's pain points and service based on their description
import asyncio
import logging
from typing import Dict, List
from utils.safety_checker import safe_dict, safe_list
from outreach_module.ai_email_generation import call_gemini_api

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_painpoints_and_service(enrichment_storage_queue: asyncio.Queue)->List[Dict[str, str]]:
    logger.info("Getting painpoints and service...")
    results = []

    while not enrichment_storage_queue.empty():
        # Get enrichment data
        enrichment_data = await enrichment_storage_queue.get()

        # Get original search mapping from searched_orgs
        searched_orgs = enrichment_data.get('searched_orgs', [])
        name_map = {} # {enriched_name.lower(): original_search_query}
        for s_org in searched_orgs:
            if s_org and "organizations" in s_org and s_org["organizations"]:
                enriched_name = s_org["organizations"][0].get("name", "").lower()
                original_name = s_org.get("search_query")
                if enriched_name and original_name:
                    name_map[enriched_name] = original_name

        #Get organizations from bulk_enriched_orgs
        bulk_enriched_orgs = enrichment_data.get('bulk_enriched_orgs', []) 

        bulk_enriched_organizations = [
            org
            for bulk_list in safe_list(bulk_enriched_orgs)
            for org in safe_list(safe_dict(bulk_list[0]).get("organizations")) if bulk_list
        ]

        tasks = []
        if bulk_enriched_organizations:
            for bulk_enriched_org in bulk_enriched_organizations:
                enriched_company_name = bulk_enriched_org.get("name", "")
                # Prioritize original search name for the AI call
                company_name_for_ai = name_map.get(enriched_company_name.lower(), enriched_company_name)
                
                short_description = bulk_enriched_org.get("short_description", "")
                if short_description:
                    tasks.append(ai_generated_painpoints_and_service(company_name_for_ai, short_description))

        if tasks:
            # Run all AI calls for this batch concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

    logger.info("Done getting painpoints and services")
    return results
    
# AI call to fetch painpoints and service
async def ai_generated_painpoints_and_service(company_name: str, company_description: str)->Dict[str, str]:
    prompt = f"""
        Analyze the following company information:
        Company Name: {company_name}
        Description: {company_description}

        Based on this, return a JSON object with:
        1. "company_name": {company_name} (CRITICAL: Return this EXACT string, do not modify it)
        2. "painpoints": A list of up to 3 most urgent technical or business pain points. 
           CRITICAL: These MUST be extracted or directly inferred from the provided Description. 
           DO NOT hallucinate or assume general industry problems. 
           If the description is very short, only include what is actually there.
        3. "service": Categorize their most needed service into EXACTLY one of these two:
           - 'ai/ml': Use this if they need AI, machine learning, data science, or automated insights.
           - 'software development international': Use this if they are primarily looking for general software engineering, web/mobile development, or scaling their development team.

        Crucially, if the company IS a software development company looking to grow its OWN team (like a dev shop or tech firm), their service need is 'software development international', NOT 'ai/ml' unless they specifically mention AI/ML challenges.

        Return ONLY valid JSON in this format:
        {{
            "company_name": "{company_name}",
            "painpoints": ["example pain point 1", "example pain point 2"],
            "service": "software development international"
        }}
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
        # Test Case 1: Multiple Orgs in one batch
        enriched_data_1 = {
            "bulk_enriched_orgs": [[{
                "organizations": [
                    {
                        "name": "Adept Technologies",
                        "short_description": "Adept Technologies is a software development company that is currently looking to grow its software development team."
                    },
                    {
                        "name": "AI Solutions Inc",
                        "short_description": "We provide cutting-edge AI and ML solutions for healthcare data processing."
                    }
                ]
            }]]
        }

        # Test Case 2: Another batch in the queue
        enriched_data_2 = {
            "bulk_enriched_orgs": [[{
                "organizations": [
                    {
                        "name": "Web Scale Corp",
                        "short_description": "Specializing in high-performance web applications and mobile development."
                    }
                ]
            }]]
        }

        enrichment_storage_queue = asyncio.Queue()
        await enrichment_storage_queue.put(enriched_data_1)
        await enrichment_storage_queue.put(enriched_data_2)
        
        results = await get_painpoints_and_service(enrichment_storage_queue)
        for i, res in enumerate(results):
            print(f"Result {i+1}: {res}")

    asyncio.run(main())

    
