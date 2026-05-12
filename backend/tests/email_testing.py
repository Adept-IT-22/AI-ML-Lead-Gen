import asyncio
import logging
logger = logging.getLogger()
from services.db_service import *
from services.email_sending import *
logging.basicConfig(level=logging.INFO)

#==============5. EMAIL================
null = None
async def main():
    logger.info("Sending emails...")
    list_of_people_in_db = [
  {
    "apollo_id": "66ff12a1ab98c20001f4d003",
    "contacted_status": "uncontacted",
    "created_at": null,
    "departments": [
      "product"
    ],
    "email": "m10mathenge@gmail.com",
    "email_status": "verified",
    "first_name": "Charlie",
    "full_name": "Charlie Murphy",
    "functions": [
      "product_management"
    ],
    "headline": "Product Manager",
    "id": 12,
    "last_name": "Murphy",
    "linkedin_url": "http://www.linkedin.com/in/charliemurphy",
    "notes": null,
    "number": "+254700000003",
    "organization_id" : "5b15515da6da987143af39cf",
    "seniority": "senior",
    "subdepartments": [
      "management"
    ],
    "title": "Senior Product Manager",
    "updated_at": null
  }
]


    for person in list_of_people_in_db:
        contacted_status = person.get("contacted_status", "")
        persons_email = person.get("email", "")

        if contacted_status == "uncontacted" and persons_email:
            persons_company_apollo_id = person.get("organization_id", "")
            persons_company = await fetch_company_by_apollo_id(persons_company_apollo_id)
            data_source = persons_company.get("company_data_source", "")
            email_to = persons_email
            first_name = person.get("first_name")
            company_name = persons_company.get("name")
            logger.info(f"Company about is: {company_name}, {first_name}, {email_to}, {data_source}")

            async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size = 10) as pool:
                if data_source == "funding":
                    funding_round = persons_company.get("latest_funding_round")
                    logger.info(f"Latest funding round: {funding_round}")
                    if not funding_round or funding_round == "Other":
                        extra_info = "latest"
                    else:
                        extra_info = str(funding_round)

                    logger.info(f"Extra info is: {extra_info}")
                        
                elif data_source == "hiring":
                    hiring_area = await get_hiring_area(company_name, pool) 
                    if hiring_area:
                        extra_info = str(hiring_area)
                    else:
                        extra_info = "various areas"

                response = await send_email(
                    data_source=data_source,
                    email_to=email_to,
                    first_name=first_name,
                    company_name=company_name,
                    extra_info=extra_info
                )

                logger.info(f"The response is: {response.status_code}...\n{response.headers}")

                #Change contacted_status in database
                #persons_apollo_id = person.get("apollo_id", "")
                #await change_person_contacted_status(persons_apollo_id, pool)
            logger.info("DONE!!!")
        else:
            logger.info(f"Contacted Status: {contacted_status}\nPerson's email: {persons_email}")

if __name__ == "__main__":
    asyncio.run(main())