import asyncio
import json
import aiofiles
import asyncpg
import logging
from services.email_sending import send_email
from services.db_service import fetch_uncontacted_people, fetch_company_by_apollo_id, get_hiring_area
from outreach_module.ai_email_generation import call_gemini_api
from utils.prompts.email_generation_prompt import get_email_generation_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
async def main(pool):
    logger.info("Sending emails...")
    list_of_people_in_db = await fetch_uncontacted_people(pool)

    description_email_match = {}
    company_set = set()

    for person in list_of_people_in_db:
        try:
            persons_email = person.get("email", "")

            # Fetch company info
            persons_company_apollo_id = person.get("organization_id", "")
            persons_company = await fetch_company_by_apollo_id(persons_company_apollo_id)
            if not persons_company:
                logger.warning(f"No company found for person {person.get('first_name')} with apollo ID {persons_company_apollo_id}")
                continue

            # Prepare email data
            company_description = persons_company.get("short_description")
            data_source = persons_company.get("company_data_source", "")
            latest_funding_round = persons_company.get("latest_funding_round", "latest")
            email_to = persons_email
            first_name = person.get("first_name")
            company_name = persons_company.get("name")
            
            logger.info(f"Preparing email for {first_name} ({email_to}) at {company_name}")

            if data_source not in ("funding", "hiring"):
                logger.warning(f"Unknown data source {data_source} for {company_name}")
                continue

            # Get prompt
            if data_source == "funding":
                prompt = get_email_generation_prompt(
                    company_description=company_description,
                    first_name = str(first_name).title(),
                    company_name=str(company_name).title(),
                    trigger_type=data_source,
                    funding_round=latest_funding_round
                ) 

            if data_source == "hiring":
                fetched_hiring_area = await get_hiring_area(company_name, pool) 
                hiring_area = fetched_hiring_area if fetched_hiring_area else "various areas"
                prompt = get_email_generation_prompt(
                    company_description=company_description,
                    first_name = first_name,
                    company_name=company_name,
                    trigger_type=data_source,
                    hiring_area=hiring_area
                )

            #Get AI generated email
            try:
                ai_response = await call_gemini_api(prompt)
                json_string = ai_response.text
                
                # 2. Parse the JSON string into a Python dictionary
                email_data = json.loads(json_string)
                
                # 3. Rename "body" to "body_html" for consistency with your previous code
                #email_data["subject"] = email_data.pop("subject")
                #email_data["body_html"] = email_data.pop("body")

                subject = email_data['subject']
                content = email_data['content']

                if company_name in company_set:
                    logger.info("Company already logged")
                    continue
                else:
                    company_set.add(company_name)
                    description_email_match[company_name] = {
                        'description': company_description,
                        'subject': subject,
                        'content': content
                    }
                    logger.info("Company logging done")
                
            except Exception as e:
                logger.exception("LLM failed to generate email: %s", str(e))


        
            ## Send individual email
            #response = await send_email(
                #email_to=email_to,
                #subject = ai_response.get("subject"),
                #content = ai_response.get("body_html")
            #)

            ## Add delay between emails
            #if response and response.status_code == 202:
                #logger.info(f"✅ Email sent successfully to {email_to}")
                #await asyncio.sleep(1)  # Rate limiting - 1 second between emails
            #else:
                #logger.error(f"❌ Failed to send email to {email_to} - Status: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Failed to process email for {person.get('first_name', 'Unknown')}: {str(e)}")
            continue

    async with aiofiles.open("email_prompts.txt", "a") as file:
        await file.writelines(json.dumps(description_email_match, indent=2))

    logger.info("Email sending complete")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    DB_URL = os.getenv("DEV_DATABASE_URL")
    async def mainn():
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=100) as pool:
            await main(pool)
    asyncio.run(mainn())
