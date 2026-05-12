import logging
import asyncio
from typing import Dict, List
from utils.db_queries import people_query
from services.db_service import store_to_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def people_storage(searched_people: Dict[str, Any], enriched_people: List[Any]):
    logger.info("Storing people data...")
    people_data_to_store = []

    people_search_data = searched_people.get("people") if searched_people else []
    people_enrichment_data = enriched_people

    if people_search_data and people_enrichment_data:
        for person_search_data, person_enrichment_data in zip(people_search_data, people_enrichment_data):
            try:
                #From people search API
                apollo_user_id = person_search_data.get("id", "")
                user_title = person_search_data.get("title", "")
                user_email_status = person_search_data.get("email_status", "")
                user_headline = person_search_data.get("headline", "")
                user_seniority = person_search_data.get("seniority", "")
                user_departments = person_search_data.get("departments", [])
                user_subdepartments = person_search_data.get("subdepartments", [])
                user_functions = person_search_data.get("functions", [])

                #From people enrichment API
                user_email = person_enrichment_data.get("person", {}).get("email", "")
                user_organization_id = person_enrichment_data.get("person", {}).get("organization_id", "")
                user_first_name = person_enrichment_data.get("person", {}).get("first_name", "")
                user_last_name = person_enrichment_data.get("person", {}).get("last_name", "")
                user_full_name = person_enrichment_data.get("person", {}).get("name", "")
                user_linkedin_url = person_enrichment_data.get("person", {}).get("linkedin_url", "")
                user_phone_number = None

                #user_phone_number_data = person_enrichment_data.get("phone_numbers", [])
                #if user_phone_number_data:
                    #user_phone_number = user_phone_number_data[0].get("sanitized_number", "")

                people_row = (apollo_user_id, user_first_name, user_last_name, user_full_name,
                                user_linkedin_url, user_title, user_email_status, user_headline,
                                user_organization_id, user_seniority, user_departments, 
                                user_subdepartments, user_functions, user_email, user_phone_number,
                                None, #notes
                            ) 

                people_data_to_store.append(people_row)

            except Exception as e:
                logger.error(f"Failed to process people data for storage: {str(e)}")
                continue

    if people_data_to_store:
        await store_to_db(data_to_store=people_data_to_store, query=people_query, company_or_people="people")
    else: 
        logger.error("No people data to store in db ❌")

if __name__ == "__main__":
    async def main():
        null = None
        false = False
        true = True

        searched_people = {
        "breadcrumbs": [
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "ceo",
            "display_name": "ceo"
            },
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "sales",
            "display_name": "sales"
            },
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "founder",
            "display_name": "founder"
            },
            {
            "label": "Include people with similar titles",
            "signal_field_name": "include_similar_titles",
            "value": true,
            "display_name": "Yes"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "owner",
            "display_name": "Owner"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "founder",
            "display_name": "Founder"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "c-suite",
            "display_name": "C-suite"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "partner",
            "display_name": "Partner"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "vp",
            "display_name": "Vp"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "head",
            "display_name": "Head"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "director",
            "display_name": "Director"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "manager",
            "display_name": "Manager"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "67461f4cebc98801b0aa0f1e",
            "display_name": "SalesPatriot (YC W25)"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6492fad89474d200c3cc8ecf",
            "display_name": "Lyzr AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "68642a1665412f000dc3bd13",
            "display_name": "Socratix AI (YC S25)"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5f487e710a63ba00013301cc",
            "display_name": "Maket"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "61ec367bc47711000134e076",
            "display_name": "GRASP"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "648747c2acd90400c3a0d8d4",
            "display_name": "Legora"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5569a687736964254f2c7200",
            "display_name": "InpharmD"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5a9edd5aa6da98d932e6166b",
            "display_name": "Lucidya | \u0644\u0648\u0633\u064a\u062f\u064a\u0627"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5fcb0af8039d52000104adcf",
            "display_name": "Nanovate"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "60ec025475d15d00a42c4b00",
            "display_name": "VeroSkills"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6493ce2aeb859c00f1fcf890",
            "display_name": "Campfire"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "57c4f256a6da986a37a2a5e0",
            "display_name": "Insight Global"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "556d0a7a736964127ed37c00",
            "display_name": "Nano Dimension"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6740a230b5a18903eb23b4bc",
            "display_name": "Peec AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5e55c8b1cbdf4b0001e58e43",
            "display_name": "Sublime Security"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "65fc68bd0fcaa50007d1a307",
            "display_name": "Polygraf AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "54a13c7469702d231f282d02",
            "display_name": "Mindhive Global"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5a9f458ea6da98d97700d06c",
            "display_name": "Space4Good"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5b846c03f874f7745ead54ad",
            "display_name": "The Graph"
            },
            {
            "label": "Company Domains",
            "signal_field_name": "q_organization_domains_list",
            "value": [
                "salespatriot.com",
                "lyzr.ai",
                "getsocratix.ai",
                "maket.ai",
                "graspfestival.dk",
                "legora.com",
                "inpharmd.com",
                "lucidya.com",
                "nanovate.io",
                "veroskills.com",
                "campfire.ai",
                "insightglobal.com",
                "nano-di.com",
                "peec.ai",
                "sublime.security",
                "polygraf.ai",
                "mindhiveglobal.com",
                "space4good.com",
                "thegraph.com"
            ],
            "display_name": "salespatriot.com, lyzr.ai and 17 other"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "verified",
            "display_name": "Verified"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "unverified",
            "display_name": "Unverified"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "likely to engage",
            "display_name": "Likely to engage"
            }
        ],
        "partial_results_only": false,
        "has_join": false,
        "disable_eu_prospecting": false,
        "partial_results_limit": 10000,
        "pagination": {
            "page": 1,
            "per_page": 10,
            "total_entries": 227,
            "total_pages": 23
        },
        "contacts": [],
        "people": [
            {
            "id": "68ff683d95ad8400016051c8",
            "first_name": "Max",
            "last_name": "Junestrand",
            "name": "Max Junestrand",
            "linkedin_url": "http://www.linkedin.com/in/maxjunestrand",
            "title": "CEO & Co-founder",
            "email_status": "verified",
            "photo_url": "https://media.licdn.com/dms/image/v2/D4D03AQFod8o4r7f0rw/profile-displayphoto-shrink_200_200/B4DZUd4gZYGcAY-/0/1739963107406?e=2147483647&v=beta&t=cgEOoyyxN6AxZHyl-3shLJt3xDTDDKwFATvygLHJrcQ",
            "twitter_url": null,
            "github_url": null,
            "facebook_url": null,
            "extrapolated_email_confidence": null,
            "headline": "CEO at Legora",
            "email": "email_not_unlocked@domain.com",
            "organization_id": "648747c2acd90400c3a0d8d4",
            "employment_history": [
                {
                "_id": "69039e22bb27600001b405ee",
                "created_at": null,
                "current": true,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": null,
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "648747c2acd90400c3a0d8d4",
                "organization_name": "Legora",
                "raw_address": null,
                "start_date": "2023-05-01",
                "title": "CEO & Co-founder",
                "updated_at": null,
                "id": "69039e22bb27600001b405ee",
                "key": "69039e22bb27600001b405ee"
                },
                {
                "_id": "69039e22bb27600001b405ef",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2023-01-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5f9953ebf701a000be3c2428",
                "organization_name": "Norrsken VC",
                "raw_address": null,
                "start_date": "2022-09-01",
                "title": "VC",
                "updated_at": null,
                "id": "69039e22bb27600001b405ef",
                "key": "69039e22bb27600001b405ef"
                },
                {
                "_id": "69039e22bb27600001b405f0",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-09-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "57c4bda8a6da9836a2b01885",
                "organization_name": "Norrsken",
                "raw_address": null,
                "start_date": "2022-07-01",
                "title": "VC",
                "updated_at": null,
                "id": "69039e22bb27600001b405f0",
                "key": "69039e22bb27600001b405f0"
                },
                {
                "_id": "69039e22bb27600001b405f1",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-07-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5ed1b7a0a363380001c0952d",
                "organization_name": "Bemlo (YC W22)",
                "raw_address": null,
                "start_date": "2022-06-01",
                "title": "Growth",
                "updated_at": null,
                "id": "69039e22bb27600001b405f1",
                "key": "69039e22bb27600001b405f1"
                },
                {
                "_id": "69039e22bb27600001b405f2",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-06-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5f4a5607938e740001fd17fa",
                "organization_name": "McKinsey & Company",
                "raw_address": null,
                "start_date": "2022-04-01",
                "title": "Business Analyst Intern",
                "updated_at": null,
                "id": "69039e22bb27600001b405f2",
                "key": "69039e22bb27600001b405f2"
                },
                {
                "_id": "69039e22bb27600001b405f3",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-04-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5e55e43971bea9000159e411",
                "organization_name": "Depict",
                "raw_address": null,
                "start_date": "2022-03-01",
                "title": "Growth Team Intern",
                "updated_at": null,
                "id": "69039e22bb27600001b405f3",
                "key": "69039e22bb27600001b405f3"
                },
                {
                "_id": "69039e22bb27600001b405f4",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-04-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "57c4bda8a6da9836a2b01885",
                "organization_name": "Norrsken",
                "raw_address": null,
                "start_date": "2022-01-01",
                "title": "Investment Team",
                "updated_at": null,
                "id": "69039e22bb27600001b405f4",
                "key": "69039e22bb27600001b405f4"
                },
                {
                "_id": "69039e22bb27600001b405f5",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2021-05-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "556dd8e7736964126c49af01",
                "organization_name": "Abios",
                "raw_address": null,
                "start_date": "2020-07-01",
                "title": "Software Engineer",
                "updated_at": null,
                "id": "69039e22bb27600001b405f5",
                "key": "69039e22bb27600001b405f5"
                },
                {
                "_id": "69039e22bb27600001b405f6",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2020-07-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "556dd8e7736964126c49af01",
                "organization_name": "Abios",
                "raw_address": null,
                "start_date": "2020-06-01",
                "title": "Back End Engineer",
                "updated_at": null,
                "id": "69039e22bb27600001b405f6",
                "key": "69039e22bb27600001b405f6"
                },
                {
                "_id": "69039e22bb27600001b405f7",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2018-09-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5d0ab44df6512508ccbe934c",
                "organization_name": "Ericsson",
                "raw_address": null,
                "start_date": "2018-07-01",
                "title": "Developer R&D",
                "updated_at": null,
                "id": "69039e22bb27600001b405f7",
                "key": "69039e22bb27600001b405f7"
                },
                {
                "_id": "69039e22bb27600001b405f8",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2017-08-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": null,
                "organization_name": "Dalar\u00f6 Seglarskola",
                "raw_address": null,
                "start_date": "2014-06-01",
                "title": "Sailing Instructor",
                "updated_at": null,
                "id": "69039e22bb27600001b405f8",
                "key": "69039e22bb27600001b405f8"
                }
            ]
            }
        ],
            "street_address": "",
            "city": "Stockholm",
            "state": "Stockholm County",
            "country": "Sweden",
            "postal_code": null,
            "formatted_address": "Stockholm, Sweden",
            "time_zone": "Europe/Stockholm",
            "organization": {
                "id": "648747c2acd90400c3a0d8d4",
                "name": "Legora",
                "website_url": "http://www.legora.com",
                "blog_url": null,
                "angellist_url": null,
                "linkedin_url": "http://www.linkedin.com/company/wearelegora",
                "twitter_url": "https://twitter.com/WeAreLegora",
                "facebook_url": null,
                "primary_phone": {
                "number": "(981) 991-1001",
                "source": "Scraped",
                "sanitized_number": "+19819911001"
                },
                "languages": [],
                "alexa_ranking": null,
                "phone": "(981) 991-1001",
                "linkedin_uid": "93196471",
                "founded_year": 2023,
                "publicly_traded_symbol": null,
                "publicly_traded_exchange": null,
                "logo_url": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68efcc1cc4daf30001099074/picture",
                "crunchbase_url": null,
                "primary_domain": "legora.com",
                "sic_codes": [
                "7375"
                ],
                "naics_codes": [
                "54111"
                ],
                "sanitized_phone": "+19819911001",
                "organization_headcount_six_month_growth": 3.333333333333333,
                "organization_headcount_twelve_month_growth": 2.25,
                "organization_headcount_twenty_four_month_growth": 12.0
            },
            "departments": [
                "c_suite"
            ],
            "subdepartments": [
                "executive",
                "founder"
            ],
            "seniority": "founder",
            "functions": [
                "entrepreneurship"
            ],
            "intent_strength": null,
            "show_intent": true,
            "email_domain_catchall": false,
            "revealed_for_current_team": true
            }


        enriched_people = {
        "breadcrumbs": [
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "ceo",
            "display_name": "ceo"
            },
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "sales",
            "display_name": "sales"
            },
            {
            "label": "Include titles",
            "signal_field_name": "person_titles",
            "value": "founder",
            "display_name": "founder"
            },
            {
            "label": "Include people with similar titles",
            "signal_field_name": "include_similar_titles",
            "value": true,
            "display_name": "Yes"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "owner",
            "display_name": "Owner"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "founder",
            "display_name": "Founder"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "c-suite",
            "display_name": "C-suite"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "partner",
            "display_name": "Partner"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "vp",
            "display_name": "Vp"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "head",
            "display_name": "Head"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "director",
            "display_name": "Director"
            },
            {
            "label": "Management Level",
            "signal_field_name": "person_seniorities",
            "value": "manager",
            "display_name": "Manager"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "67461f4cebc98801b0aa0f1e",
            "display_name": "SalesPatriot (YC W25)"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6492fad89474d200c3cc8ecf",
            "display_name": "Lyzr AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "68642a1665412f000dc3bd13",
            "display_name": "Socratix AI (YC S25)"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5f487e710a63ba00013301cc",
            "display_name": "Maket"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "61ec367bc47711000134e076",
            "display_name": "GRASP"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "648747c2acd90400c3a0d8d4",
            "display_name": "Legora"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5569a687736964254f2c7200",
            "display_name": "InpharmD"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5a9edd5aa6da98d932e6166b",
            "display_name": "Lucidya | \u0644\u0648\u0633\u064a\u062f\u064a\u0627"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5fcb0af8039d52000104adcf",
            "display_name": "Nanovate"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "60ec025475d15d00a42c4b00",
            "display_name": "VeroSkills"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6493ce2aeb859c00f1fcf890",
            "display_name": "Campfire"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "57c4f256a6da986a37a2a5e0",
            "display_name": "Insight Global"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "556d0a7a736964127ed37c00",
            "display_name": "Nano Dimension"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "6740a230b5a18903eb23b4bc",
            "display_name": "Peec AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5e55c8b1cbdf4b0001e58e43",
            "display_name": "Sublime Security"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "65fc68bd0fcaa50007d1a307",
            "display_name": "Polygraf AI"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "54a13c7469702d231f282d02",
            "display_name": "Mindhive Global"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5a9f458ea6da98d97700d06c",
            "display_name": "Space4Good"
            },
            {
            "label": "Companies",
            "signal_field_name": "organization_ids",
            "value": "5b846c03f874f7745ead54ad",
            "display_name": "The Graph"
            },
            {
            "label": "Company Domains",
            "signal_field_name": "q_organization_domains_list",
            "value": [
                "salespatriot.com",
                "lyzr.ai",
                "getsocratix.ai",
                "maket.ai",
                "graspfestival.dk",
                "legora.com",
                "inpharmd.com",
                "lucidya.com",
                "nanovate.io",
                "veroskills.com",
                "campfire.ai",
                "insightglobal.com",
                "nano-di.com",
                "peec.ai",
                "sublime.security",
                "polygraf.ai",
                "mindhiveglobal.com",
                "space4good.com",
                "thegraph.com"
            ],
            "display_name": "salespatriot.com, lyzr.ai and 17 other"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "verified",
            "display_name": "Verified"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "unverified",
            "display_name": "Unverified"
            },
            {
            "label": "Email Status",
            "signal_field_name": "contact_email_status",
            "value": "likely to engage",
            "display_name": "Likely to engage"
            }
        ],
        "partial_results_only": false,
        "has_join": false,
        "disable_eu_prospecting": false,
        "partial_results_limit": 10000,
        "pagination": {
            "page": 1,
            "per_page": 10,
            "total_entries": 227,
            "total_pages": 23
        },
        "contacts": [],
        "people": [
            {
            "id": "68ff683d95ad8400016051c8",
            "first_name": "Max",
            "last_name": "Junestrand",
            "name": "Max Junestrand",
            "linkedin_url": "http://www.linkedin.com/in/maxjunestrand",
            "title": "CEO & Co-founder",
            "email_status": "verified",
            "photo_url": "https://media.licdn.com/dms/image/v2/D4D03AQFod8o4r7f0rw/profile-displayphoto-shrink_200_200/B4DZUd4gZYGcAY-/0/1739963107406?e=2147483647&v=beta&t=cgEOoyyxN6AxZHyl-3shLJt3xDTDDKwFATvygLHJrcQ",
            "twitter_url": null,
            "github_url": null,
            "facebook_url": null,
            "extrapolated_email_confidence": null,
            "headline": "CEO at Legora",
            "email": "email_not_unlocked@domain.com",
            "organization_id": "648747c2acd90400c3a0d8d4",
            "employment_history": [
                {
                "_id": "69039e22bb27600001b405ee",
                "created_at": null,
                "current": true,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": null,
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "648747c2acd90400c3a0d8d4",
                "organization_name": "Legora",
                "raw_address": null,
                "start_date": "2023-05-01",
                "title": "CEO & Co-founder",
                "updated_at": null,
                "id": "69039e22bb27600001b405ee",
                "key": "69039e22bb27600001b405ee"
                },
                {
                "_id": "69039e22bb27600001b405ef",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2023-01-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5f9953ebf701a000be3c2428",
                "organization_name": "Norrsken VC",
                "raw_address": null,
                "start_date": "2022-09-01",
                "title": "VC",
                "updated_at": null,
                "id": "69039e22bb27600001b405ef",
                "key": "69039e22bb27600001b405ef"
                },
                {
                "_id": "69039e22bb27600001b405f0",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-09-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "57c4bda8a6da9836a2b01885",
                "organization_name": "Norrsken",
                "raw_address": null,
                "start_date": "2022-07-01",
                "title": "VC",
                "updated_at": null,
                "id": "69039e22bb27600001b405f0",
                "key": "69039e22bb27600001b405f0"
                },
                {
                "_id": "69039e22bb27600001b405f1",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-07-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5ed1b7a0a363380001c0952d",
                "organization_name": "Bemlo (YC W22)",
                "raw_address": null,
                "start_date": "2022-06-01",
                "title": "Growth",
                "updated_at": null,
                "id": "69039e22bb27600001b405f1",
                "key": "69039e22bb27600001b405f1"
                },
                {
                "_id": "69039e22bb27600001b405f2",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-06-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5f4a5607938e740001fd17fa",
                "organization_name": "McKinsey & Company",
                "raw_address": null,
                "start_date": "2022-04-01",
                "title": "Business Analyst Intern",
                "updated_at": null,
                "id": "69039e22bb27600001b405f2",
                "key": "69039e22bb27600001b405f2"
                },
                {
                "_id": "69039e22bb27600001b405f3",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-04-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5e55e43971bea9000159e411",
                "organization_name": "Depict",
                "raw_address": null,
                "start_date": "2022-03-01",
                "title": "Growth Team Intern",
                "updated_at": null,
                "id": "69039e22bb27600001b405f3",
                "key": "69039e22bb27600001b405f3"
                },
                {
                "_id": "69039e22bb27600001b405f4",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2022-04-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "57c4bda8a6da9836a2b01885",
                "organization_name": "Norrsken",
                "raw_address": null,
                "start_date": "2022-01-01",
                "title": "Investment Team",
                "updated_at": null,
                "id": "69039e22bb27600001b405f4",
                "key": "69039e22bb27600001b405f4"
                },
                {
                "_id": "69039e22bb27600001b405f5",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2021-05-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "556dd8e7736964126c49af01",
                "organization_name": "Abios",
                "raw_address": null,
                "start_date": "2020-07-01",
                "title": "Software Engineer",
                "updated_at": null,
                "id": "69039e22bb27600001b405f5",
                "key": "69039e22bb27600001b405f5"
                },
                {
                "_id": "69039e22bb27600001b405f6",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2020-07-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "556dd8e7736964126c49af01",
                "organization_name": "Abios",
                "raw_address": null,
                "start_date": "2020-06-01",
                "title": "Back End Engineer",
                "updated_at": null,
                "id": "69039e22bb27600001b405f6",
                "key": "69039e22bb27600001b405f6"
                },
                {
                "_id": "69039e22bb27600001b405f7",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2018-09-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": "5d0ab44df6512508ccbe934c",
                "organization_name": "Ericsson",
                "raw_address": null,
                "start_date": "2018-07-01",
                "title": "Developer R&D",
                "updated_at": null,
                "id": "69039e22bb27600001b405f7",
                "key": "69039e22bb27600001b405f7"
                },
                {
                "_id": "69039e22bb27600001b405f8",
                "created_at": null,
                "current": false,
                "degree": null,
                "description": null,
                "emails": null,
                "end_date": "2017-08-01",
                "grade_level": null,
                "kind": null,
                "major": null,
                "organization_id": null,
                "organization_name": "Dalar\u00f6 Seglarskola",
                "raw_address": null,
                "start_date": "2014-06-01",
                "title": "Sailing Instructor",
                "updated_at": null,
                "id": "69039e22bb27600001b405f8",
                "key": "69039e22bb27600001b405f8"
                }
            ]
            }
        ],
            "street_address": "",
            "city": "Stockholm",
            "state": "Stockholm County",
            "country": "Sweden",
            "postal_code": null,
            "formatted_address": "Stockholm, Sweden",
            "time_zone": "Europe/Stockholm",
            "organization": {
                "id": "648747c2acd90400c3a0d8d4",
                "name": "Legora",
                "website_url": "http://www.legora.com",
                "blog_url": null,
                "angellist_url": null,
                "linkedin_url": "http://www.linkedin.com/company/wearelegora",
                "twitter_url": "https://twitter.com/WeAreLegora",
                "facebook_url": null,
                "primary_phone": {
                "number": "(981) 991-1001",
                "source": "Scraped",
                "sanitized_number": "+19819911001"
                },
                "languages": [],
                "alexa_ranking": null,
                "phone": "(981) 991-1001",
                "linkedin_uid": "93196471",
                "founded_year": 2023,
                "publicly_traded_symbol": null,
                "publicly_traded_exchange": null,
                "logo_url": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68efcc1cc4daf30001099074/picture",
                "crunchbase_url": null,
                "primary_domain": "legora.com",
                "sic_codes": [
                "7375"
                ],
                "naics_codes": [
                "54111"
                ],
                "sanitized_phone": "+19819911001",
                "organization_headcount_six_month_growth": 3.333333333333333,
                "organization_headcount_twelve_month_growth": 2.25,
                "organization_headcount_twenty_four_month_growth": 12.0
            },
            "departments": [
                "c_suite"
            ],
            "subdepartments": [
                "executive",
                "founder"
            ],
            "seniority": "founder",
            "functions": [
                "entrepreneurship"
            ],
            "intent_strength": null,
            "show_intent": true,
            "email_domain_catchall": false,
            "revealed_for_current_team": true
            },

        await people_storage(searched_people, enriched_people)
    
    asyncio.run(main())
