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
    "apollo_id": "57c50413a6da986a1b2874fa",
    "contacted_status": "uncontacted",
    "created_at": null,
    "departments": [
      "engineering"
    ],
    "email": "m10mathenge@gmail.com",
    "email_status": "verified",
    "first_name": "Mark",
    "full_name": "Mark Mathenge",
    "functions": [
      "software_engineering"
    ],
    "headline": "Software Engineer",
    "id": 10,
    "last_name": "Mathenge",
    "linkedin_url": "http://www.linkedin.com/in/markmathenge",
    "notes": null,
    "number": "+254700000001",
    "organization_id" :"60f3c5498dbf150001e70682",
    "seniority": "mid_level",
    "subdepartments": [
      "backend"
    ],
    "title": "Backend Engineer",
    "updated_at": null
  },
  {
    "apollo_id": "66ff12a1ab98c20001f4d002",
    "contacted_status": "uncontacted",
    "created_at": null,
    "departments": [
      "c_suite"
    ],
    "email": "mark.mathenge@riarauniversity.com",
    "email_status": "verified",
    "first_name": "James",
    "full_name": "James Bond",
    "functions": [
      "entrepreneurship"
    ],
    "headline": "Founder & CEO",
    "id": 11,
    "last_name": "Bond",
    "linkedin_url": "http://www.linkedin.com/in/jamesbond",
    "notes": null,
    "number": "+254700000002",
    "organization_id" :"60f3c5498dbf150001e70682",
    "seniority": "founder",
    "subdepartments": [
      "founder"
    ],
    "title": "CEO",
    "updated_at": null
  },
  {
    "apollo_id": "66ff12a1ab98c20001f4d003",
    "contacted_status": "uncontacted",
    "created_at": null,
    "departments": [
      "product"
    ],
    "email": "codeinekaepernick@gmail.com",
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
    "organization_id" :"60f3c5498dbf150001e70682",
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
                    if funding_round:
                        extra_info = str(funding_round)
                    else:
                        extra_info = "latest"
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

                logger.info(f"The response is: {response}")

                #Change contacted_status in database
                #persons_apollo_id = person.get("apollo_id", "")
                #await change_person_contacted_status(persons_apollo_id, pool)
            logger.info("DONE!!!")
        else:
            logger.info(f"Contacted Status: {contacted_status}\nPerson's email: {persons_email}")

if __name__ == "__main__":
    asyncio.run(main())