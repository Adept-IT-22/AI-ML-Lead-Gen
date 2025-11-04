import asyncio
import asyncpg
import logging
from services.email_sending import send_email
from services.db_service import fetch_uncontacted_people, fetch_company_by_apollo_id, get_hiring_area

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
async def main(pool):
    logger.info("Sending emails...")
    list_of_people_in_db = await fetch_uncontacted_people(pool)

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
            data_source = persons_company.get("company_data_source", "")
            latest_funding_round = persons_company.get("latest_funding_round", "")
            email_to = persons_email
            first_name = person.get("first_name")
            company_name = persons_company.get("name")
            
            logger.info(f"Preparing email for {first_name} ({email_to}) at {company_name}")

            # Get extra info based on data source
            if data_source == "funding" and latest_funding_round not in ['Seed', 'Series A', 'Series B']:
                extra_info = "latest" if not latest_funding_round or latest_funding_round == "Other" else str(latest_funding_round)
            elif data_source == "hiring":
                hiring_area = await get_hiring_area(company_name, pool)
                extra_info = str(hiring_area) if hiring_area else "various areas"
            else:
                logger.warning(f"Unknown data source {data_source} for {company_name}")
                continue

            # Send individual email
            response = await send_email(
                data_source=data_source,
                latest_funding_round=latest_funding_round,
                email_to=email_to,
                first_name=first_name,
                company_name=company_name,
                extra_info=extra_info
            )

            # Add delay between emails
            if response and response.status_code == 202:
                logger.info(f"✅ Email sent successfully to {email_to}")
                await asyncio.sleep(1)  # Rate limiting - 1 second between emails
            else:
                logger.error(f"❌ Failed to send email to {email_to} - Status: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Failed to process email for {person.get('first_name', 'Unknown')}: {str(e)}")
            continue

    logger.info("Email sending complete")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    DB_URL = os.getenv("DEV_DATABASE_URL")
    async def demo():
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await main(pool)

    asyncio.run(demo())