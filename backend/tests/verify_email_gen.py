import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outreach_module.ai_email_generation import call_gemini_api
from utils.prompts.email_generation_prompt import get_email_generation_prompt

async def verify_prompts():
    #company_description = "Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software that analyzes advertising creatives to identify effective design elements and messaging."
    company_description = "ManageMy is a SaaS technology company based in Charlotte, North Carolina, founded in 2018. The company specializes in an AI-driven digital platform designed for insurance carriers. This platform helps streamline various processes such as buying, underwriting, servicing, and claims, while also driving sales growth and enhancing customer experiences without the need to overhaul existing legacy systems. One of the key offerings is XPerience Studio, a no-code API-based solution that allows carriers to quickly configure workflows, forms, and digital journeys across multiple platforms. The digital front-end platform supports the entire policy lifecycle, including quoting, onboarding, and claims management. Additionally, ManageMy provides integrated marketing services through MyCustomer, which focuses on data-driven campaigns for upselling and retention. The company leverages a team with extensive insurance expertise, emphasizing cybersecurity and regulatory compliance to support its clients effectively."
    first_name = "Jane"
    company_name = "ManageMy"
    
    # Test 1: Hiring trigger with painpoints
    hiring_area = "Software Engineering"
    painpoints = ["Scaling the software engineering team"]
    
    print("\n--- TESTING HIRING PROMPT ---")
    prompt = get_email_generation_prompt(
        company_description=company_description,
        first_name=first_name,
        company_name=company_name,
        trigger_type="hiring",
        sequence_number=4,
        hiring_area=hiring_area,
        painpoints=painpoints
    )
    
    #print("PROMPT PREVIEW (First 500 chars):")
    #print(prompt[:500] + "...")
    
    response = await call_gemini_api(prompt)
    if response:
        text = response.candidates[0].content.parts[0].text
        print("\nGENERATED EMAIL (HIRING):")
        print(text)
        
    # Test 2: Funding trigger with painpoints
    print("\n--- TESTING FUNDING PROMPT ---")
    prompt_f = get_email_generation_prompt(
        company_description=company_description,
        first_name=first_name,
        company_name=company_name,
        trigger_type="funding",
        sequence_number=4,
        funding_round="Series B",
        painpoints=["Scaling operational throughput", "Maintaining QA standards during rapid growth"]
    )
    
    response_f = await call_gemini_api(prompt_f)
    if response_f:
        text_f = response_f.candidates[0].content.parts[0].text
        print("\nGENERATED EMAIL (FUNDING):")
        print(text_f)

if __name__ == "__main__":
    asyncio.run(verify_prompts())
