import asyncpg
import asyncio
import logging
from typing import List
from utils.db_queries import company_query
from helpers.helpers import safe_int, safe_decimal
from utils.data_normalization import normalize_amount_raised
from utils.safety_checker import safe_dict, safe_list
from services.db_service import store_to_db, is_company_in_db, fetch_source_link, fetch_funding_details

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Store company data
async def company_storage(pool: asyncpg.Pool, all_normalized_data: List, searched_orgs: List, bulk_enriched_orgs: List, single_enriched_orgs: List):
    logger.info("Storing company data...")
    company_data_to_store = []

    searched_organizations = [
        orgs[0]
        for d in safe_list(searched_orgs)
        for orgs in [safe_list(safe_dict(d).get("organizations"))]
        if orgs
    ]

    bulk_enriched_organizations = [
        org
        for bulk_list in safe_list(bulk_enriched_orgs)
        for org in safe_list(safe_dict(bulk_list[0]).get("organizations")) if bulk_list
    ]

    single_enriched_organizations = [
        safe_dict(item).get("organization")
        for item in safe_list(single_enriched_orgs)
        if safe_dict(item).get("organization") is not None
    ]


    #Iterate over orgs
    if searched_organizations and bulk_enriched_organizations and single_enriched_organizations:
        for searched_org, bulk_enriched_org, single_enriched_organization in zip(searched_organizations, bulk_enriched_organizations, single_enriched_organizations, strict=False):
            try:
                #Get necessary data from org search 
                headcount_six_month_growth = searched_org.get("organization_headcount_six_month_growth", "")
                headcount_twelve_month_growth = searched_org.get("organization_headcount_twelve_month_growth", "")

                #Get necessary data from bulk enriched orgs
                apollo_id = bulk_enriched_org.get("id", "")
                #Check if org is in DB
                company_name = bulk_enriched_org.get("name", "")
                website_url = bulk_enriched_org.get("website_url", "")
                linkedin_url = bulk_enriched_org.get("linkedin_url", "")
                phone = bulk_enriched_org.get("phone", "")
                founded_year = bulk_enriched_org.get("founded_year", "")
                market_cap = bulk_enriched_org.get("market_cap", "")
                industries = bulk_enriched_org.get("industries", [])
                estimated_num_employees = bulk_enriched_org.get("estimated_num_employees", "")
                keywords = bulk_enriched_org.get("keywords", [])
                city = bulk_enriched_org.get("city", "")
                state = bulk_enriched_org.get("state", "")
                country = bulk_enriched_org.get("country", "")
                short_description = bulk_enriched_org.get("short_description", "")

                #Get necessary data from single enriched orgs
                total_funding = single_enriched_organization.get("total_funding", "")
                technology_names = single_enriched_organization.get("technology_names", [])
                annual_revenue_printed = single_enriched_organization.get("annual_revenue", "")
                funding_events_list = single_enriched_organization.get("funding_events", [])
                if funding_events_list:
                    latest_funding_round = funding_events_list[0].get("type") 
                    unclean_latest_funding_amount = funding_events_list[0].get("amount") 
                    latest_funding_amount = normalize_amount_raised(unclean_latest_funding_amount) if unclean_latest_funding_amount else None
                    latest_funding_currency = funding_events_list[0].get("currency") 
                else:
                    try:
                        normalized_funding_data = await fetch_funding_details(pool, company_name)
                        latest_funding_round = normalized_funding_data.get("funding_round", "")
                        latest_funding_amount = safe_int(normalized_funding_data.get("amount_raised", "0"))
                        latest_funding_currency = normalized_funding_data.get("currency", "")
                    except Exception as e:
                        logger.error(f"Failed to fetch funding details for {company_name}: {str(e)}")
                        latest_funding_round = ""
                        latest_funding_amount = None
                        latest_funding_currency = ""

                #Get data source (funding, events, hiring) from normalized data
                company_data_source = None
                painpoints = []
                service = ""
                for normalized_company_info in all_normalized_data:
                    normalized_names = normalized_company_info.get("company_name", [])
                    found_match = False
                    for idx, normalized_name in enumerate(normalized_names):
                        if normalized_name.lower() in company_name.lower() or company_name.lower() in normalized_name.lower():
                            company_data_source = normalized_company_info.get("type")
                            
                            # Extract painpoints if available
                            all_painpoints = normalized_company_info.get("painpoints", [])
                            if idx < len(all_painpoints):
                                painpoints = all_painpoints[idx]
                            
                            # Extract service if available
                            all_services = normalized_company_info.get("service", [])
                            if idx < len(all_services):
                                service = all_services[idx]
                                
                            found_match = True
                            break
                    if found_match:
                        break

                #Fix the source link fetch
                try:
                    source_link_details = await fetch_source_link(pool, company_name)
                    source_link = source_link_details.get("link", "")
                except Exception as e:
                    logger.error(f"Failed to fetch source link for {company_name}: {str(e)}")
                    source_link = ""

                #Ensure all numeric values use safe_int() or safe_decimal()
                company_row = (
                    apollo_id, 
                    company_name, 
                    website_url, 
                    linkedin_url, 
                    phone,
                    safe_int(founded_year),
                    safe_decimal(market_cap), 
                    safe_decimal(annual_revenue_printed),
                    industries,
                    safe_int(estimated_num_employees),
                    keywords,
                    safe_decimal(headcount_six_month_growth),
                    safe_decimal(headcount_twelve_month_growth),
                    city,
                    state,
                    country,
                    short_description,
                    safe_decimal(total_funding),
                    technology_names,
                    None, #icp score placeholder  
                    None,  # notes
                    company_data_source,
                    latest_funding_round,
                    latest_funding_amount,
                    latest_funding_currency,
                    source_link,
                    painpoints,
                    service
                )

                company_data_to_store.append(company_row)

            except Exception as e:
                logger.error(f"Failed to process company data for storage: {str(e)}")
                continue

    #Store company data in "companies" database
    if company_data_to_store:
        #Check if company is in db
        company_in_db = await is_company_in_db(company_name=company_name)
        if not company_in_db:
            #await store_to_db(data_to_store=company_data_to_store, query=company_query, company_or_people="company")
            logger.info("NDANI")
            return [row[0] for row in company_data_to_store] # Return apollo_ids
        else:
            logger.warning(f"{company_name} is already in DB")
            return [row[0] for row in company_data_to_store] # Return apollo_ids even if already in DB
    else:
        logger.warning("No companies to store ❌")
        return []

if __name__ == "__main__":
    async def main():
        import os
        from dotenv import load_dotenv
        load_dotenv(override=True)

        DB_URL = os.getenv("MOCK_DATABASE_URL")

        null = None
        false = False
        true = True

        all_normalized_data = [
        {
            "type": "funding",
            "source": "FinSMEs",
            "title": [],
            "link": [
            "https://www.finsmes.com/2025/09/salt-ai-raises-10m-in-funding.html",
            "https://www.finsmes.com/2025/09/wexler-ai-raises-5-3m-in-seed-funding.html",
            "https://www.finsmes.com/2025/09/manas-ai-raises-26m-in-seed-extension.html",
            "https://www.finsmes.com/2025/09/markup-ai-raises-27-5m-in-funding.html",
            "https://www.finsmes.com/2025/09/obot-ai-raises-35m-in-seed-funding.html",
            "https://www.finsmes.com/2025/09/ardent-ai-raises-2-15m-in-pre-seed-funding.html",
            "https://www.finsmes.com/2025/09/maxhome-ai-raises-5m-in-seed-funding.html",
            "https://www.finsmes.com/2025/09/upscale-ai-launches-with-over-100m-seed-funding.html",
            "https://www.finsmes.com/2025/09/distyl-ai-raises-175m-at-1-8-billion-valuation.html",
            "https://www.finsmes.com/2025/09/socialpost-ai-raises-1m-in-funding.html",
            "https://www.finsmes.com/2025/09/envive-ai-raises-15m-in-series-a-funding.html"
            ],
            "article_date": [
            "2025-09-22",
            "2025-09-23",
            "2025-09-23",
            "2025-09-18",
            "2025-09-23",
            "2025-09-26",
            "2025-09-26",
            "2025-09-17",
            "2025-09-24",
            "2025-09-25",
            "2025-09-17"
            ],
            "company_name": [
            "salt ai",
            "wexler.ai",
            "manas ai",
            "markup ai",
            "obot ai",
            "ardent ai",
            "maxhome.ai",
            "upscale ai, inc.",
            "distyl ai",
            "socialpost.ai",
            "envive ai"
            ],
            "city": [],
            "country": [],
            "company_decision_makers": [
            [
                "Aber Whitcomb"
            ],
            [
                "Gregory Mostyn"
            ],
            [
                "Dr. Siddhartha Mukherjee",
                "Reid Hoffman",
                "Ujjwal Singh"
            ],
            [
                "Matt Blumberg"
            ],
            [
                "Sheng Liang"
            ],
            [
                "Vikram Chennai"
            ],
            [
                "Divya Aathresh"
            ],
            [
                "Barun Kar",
                "Rajiv Khemani"
            ],
            [
                "Arjun Prakash",
                "Derek Ho"
            ],
            [
                "Gregory Scott Henson"
            ],
            [
                "Aniket Deosthali"
            ]
            ],
            "company_decision_makers_position": [
            [
                "Ceo"
            ],
            [
                "Ceo"
            ],
            [
                "Co-Founder",
                "Co-Founder",
                "Co-Founder"
            ],
            [
                "Ceo"
            ],
            [
                "Ceo"
            ],
            [
                "Ceo"
            ],
            [
                "Founder"
            ],
            [
                "Ceo",
                "Founder"
            ],
            [
                "Founder",
                "Founder"
            ],
            [
                "Founder And Ceo"
            ],
            [
                "Ceo"
            ]
            ],
            "funding_round": [
            "",
            "Seed",
            "Seed Extension",
            "",
            "Seed",
            "Pre-Seed",
            "Seed",
            "Seed",
            "Venture",
            "Seed",
            "Series A"
            ],
            "amount_raised": [
            "10000000",
            "5300000",
            "26000000",
            "27500000",
            "35000000",
            "2150000",
            "5000000",
            "100000000",
            "175000000",
            "1000000",
            "15000000"
            ],
            "currency": [
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar",
            "US Dollar"
            ],
            "investor_companies": [
            [
                "Morpheus Ventures",
                "Struck Capital",
                "Marbruck Investments",
                "Coreweave"
            ],
            [
                "Pear Vc",
                "Seedcamp",
                "The Legaltech Fund",
                "Myriad Venture Partners"
            ],
            [
                "The General Partnership",
                "Wisdom Ventures",
                "Blitzscaling Ventures",
                "Westbound Equity Partners",
                "Mosaic Ventures"
            ],
            [
                "Genui Partners",
                "Emh Partners",
                "Capital Factory"
            ],
            [
                "Mayfield Fund",
                "Nexus Venture Partners"
            ],
            [
                "Crane Venture Partners",
                "Active Capital"
            ],
            [
                "Fika Ventures",
                "Bbg Ventures",
                "1Sharpe Ventures",
                "Four Acres Capital"
            ],
            [
                "Mayfield",
                "Maverick Silicon",
                "Stepstone Group",
                "Celesta Capital",
                "Xora",
                "Qualcomm Ventures",
                "Cota Capital",
                "Mvp Ventures",
                "Stanford University"
            ],
            [
                "Lightspeed Venture Partners",
                "Khosla Ventures",
                "Dst Global",
                "Coatue",
                "Dell Technologies Capital"
            ],
            [
                "Ember Venture Capital"
            ],
            [
                "Fuse Vc"
            ]
            ],
            "investor_people": [
            [],
            [],
            [],
            [
                "Brad Feld",
                "Scott Dorsey",
                "David Fox",
                "Jake Heller",
                "David Kidder",
                "Bernd-Michael Rumpf",
                "Greg Sands",
                "Kindra Tatarsky"
            ],
            [],
            [
                "Zach Wilson"
            ],
            [],
            []
            ],
            "tags": [
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            []
            ],
            "painpoints": [
            ["scaling AI services"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"],
            ["AI/ML development"]
            ],
            "service": [
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML",
            "AI/ML"
            ]
        }
        ]

        searched_orgs = [
        {
            "breadcrumbs": [
            {
                "label": "Company Name",
                "signal_field_name": "q_organization_name",
                "value": "salt ai",
                "display_name": "salt ai"
            }
            ],
            "partial_results_only": false,
            "has_join": false,
            "disable_eu_prospecting": false,
            "partial_results_limit": 10000,
            "pagination": {
            "page": 1,
            "per_page": 1,
            "total_entries": 27,
            "total_pages": 27
            },
            "accounts": [],
            "organizations": [
            {
                "id": "655081d888b7c60001d3aae0",
                "name": "Salt AI",
                "website_url": "http://www.salt.ai",
                "blog_url": null,
                "angellist_url": null,
                "linkedin_url": "http://www.linkedin.com/company/getsalt-ai",
                "twitter_url": null,
                "facebook_url": null,
                "primary_phone": {},
                "languages": [],
                "alexa_ranking": null,
                "phone": null,
                "linkedin_uid": "90395337",
                "founded_year": 2024,
                "publicly_traded_symbol": null,
                "publicly_traded_exchange": null,
                "logo_url": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68d145de2144fa0001397859/picture",
                "crunchbase_url": null,
                "primary_domain": "salt.ai",
                "sic_codes": [
                "3829"
                ],
                "naics_codes": [
                "54171"
                ],
                "owned_by_organization_id": null,
                "organization_revenue_printed": null,
                "organization_revenue": 0.0,
                "intent_strength": null,
                "show_intent": true,
                "has_intent_signal_account": false,
                "intent_signal_account": null,
                "organization_headcount_six_month_growth": 0.125,
                "organization_headcount_twelve_month_growth": 0.03846153846153846,
                "organization_headcount_twenty_four_month_growth": -0.3720930232558139
            }
            ],
            "model_ids": [
            "655081d888b7c60001d3aae0"
            ],
            "num_fetch_result": null,
            "derived_params": {
            "recommendation_config_id": "68a2f508398f2a00015ce352"
            }
        }
        ]

        bulk_enriched_orgs = [[
        {
            "status": "success",
            "error_code": null,
            "error_message": null,
            "total_requested_domains": 8,
            "unique_domains": 8,
            "unique_enriched_records": 8,
            "missing_records": 0,
            "organizations": [
            {
                "id": "67461f4cebc98801b0aa0f1e",
                "name": "SalesPatriot (YC W25)",
                "website_url": "http://www.salespatriot.com",
                "blog_url": null,
                "angellist_url": null,
                "linkedin_url": "http://www.linkedin.com/company/salespatriot",
                "twitter_url": null,
                "facebook_url": null,
                "primary_phone": {
                "number": "+1 262-215-8573",
                "source": "Account",
                "sanitized_number": "+12622158573"
                },
                "languages": [],
                "alexa_ranking": null,
                "phone": "+1 262-215-8573",
                "linkedin_uid": "104985727",
                "founded_year": 2024,
                "publicly_traded_symbol": null,
                "publicly_traded_exchange": null,
                "logo_url": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68f002f6b89e5800014a4c3d/picture",
                "crunchbase_url": null,
                "primary_domain": "salespatriot.com",
                "sic_codes": [
                "7375"
                ],
                "naics_codes": [
                "54151"
                ],
                "sanitized_phone": "+12622158573",
                "industry": "defense & space",
                "estimated_num_employees": 15,
                "keywords": [
                "defense & space manufacturing",
                "defense contracting",
                "contract management",
                "supply chain insights",
                "market share growth tools",
                "cost analysis",
                "opportunity discovery",
                "competitive intelligence in defense",
                "market share increase",
                "market and competitor analysis",
                "services",
                "ai-powered bid suggestions",
                "opportunity discovery tools",
                "opportunity ranking",
                "kanban project management",
                "bid success optimization",
                "contract opportunity alerts",
                "nsn opportunity identification",
                "government contract bidding",
                "cross-department workflow",
                "government procurement analytics",
                "data security",
                "security and privacy compliance",
                "defense contractor tools",
                "opportunity matching",
                "bid automation",
                "bid pipeline automation",
                "contract management platform",
                "information technology",
                "government",
                "cost and labor tracking",
                "software development",
                "bid pipeline management",
                "bid success rate",
                "solicitation analysis",
                "manufacturing",
                "supply class analysis",
                "computer systems design and related services",
                "workflow automation",
                "supply class discovery",
                "b2b",
                "competitor tracking",
                "defense",
                "defense industry software",
                "ai opportunity matching",
                "price suggestions",
                "nsn opportunities",
                "bid analysis",
                "market insights",
                "computer & network security",
                "information technology & services",
                "mechanical or industrial engineering"
                ],
                "organization_revenue_printed": null,
                "organization_revenue": 0.0,
                "industries": [
                "defense & space"
                ],
                "secondary_industries": [],
                "snippets_loaded": true,
                "industry_tag_id": "5567e1097369641b5f810500",
                "industry_tag_hash": {
                "defense & space": "5567e1097369641b5f810500"
                },
                "retail_location_count": 0,
                "raw_address": "san francisco, california, united states",
                "street_address": "",
                "city": "San Francisco",
                "state": "California",
                "country": "United States",
                "postal_code": null,
                "owned_by_organization_id": null,
                "short_description": "Find solicitations. Bid. Win.\n\nHelping DoD manufacturers find the best solicitations and streamlining the bidding process. Get in touch and grow your business with SalesPatriot!",
                "departmental_head_count": {
                "engineering": 7,
                "consulting": 1,
                "entrepreneurship": 2,
                "information_technology": 1,
                "sales": 1,
                "business_development": 1,
                "accounting": 0,
                "operations": 0,
                "finance": 0,
                "marketing": 0,
                "human_resources": 0,
                "legal": 0,
                "product_management": 0,
                "education": 0,
                "administrative": 0,
                "media_and_commmunication": 0,
                "arts_and_design": 0,
                "support": 0,
                "data_science": 0
                },
                "intent_strength": null,
                "show_intent": false,
                "has_intent_signal_account": false,
                "intent_signal_account": null,
                "generic_org_insights": null,
                "organization_headcount_six_month_growth": null,
                "organization_headcount_twelve_month_growth": null,
                "organization_headcount_twenty_four_month_growth": null
            }
        ]
        }
        ]]

        single_enriched_orgs = [
        {
            "organization": {
            "id": "67461f4cebc98801b0aa0f1e",
            "name": "SalesPatriot (YC W25)",
            "website_url": "http://www.salespatriot.com",
            "blog_url": null,
            "angellist_url": null,
            "linkedin_url": "http://www.linkedin.com/company/salespatriot",
            "twitter_url": null,
            "facebook_url": null,
            "primary_phone": {
                "number": "+1 262-215-8573",
                "source": "Account",
                "sanitized_number": "+12622158573"
            },
            "languages": [],
            "alexa_ranking": null,
            "phone": "+1 262-215-8573",
            "linkedin_uid": "104985727",
            "founded_year": 2024,
            "publicly_traded_symbol": null,
            "publicly_traded_exchange": null,
            "logo_url": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68f002f6b89e5800014a4c3d/picture",
            "crunchbase_url": null,
            "primary_domain": "salespatriot.com",
            "sic_codes": [
                "7375"
            ],
            "naics_codes": [
                "54151"
            ],
            "sanitized_phone": "+12622158573",
            "industry": "defense & space",
            "estimated_num_employees": 15,
            "keywords": [
                "defense & space manufacturing",
                "defense contracting",
                "contract management",
                "supply chain insights",
                "market share growth tools",
                "cost analysis",
                "opportunity discovery",
                "competitive intelligence in defense",
                "market share increase",
                "market and competitor analysis",
                "services",
                "ai-powered bid suggestions",
                "opportunity discovery tools",
                "opportunity ranking",
                "kanban project management",
                "bid success optimization",
                "contract opportunity alerts",
                "nsn opportunity identification",
                "government contract bidding",
                "cross-department workflow",
                "government procurement analytics",
                "data security",
                "security and privacy compliance",
                "defense contractor tools",
                "opportunity matching",
                "bid automation",
                "bid pipeline automation",
                "contract management platform",
                "information technology",
                "government",
                "cost and labor tracking",
                "software development",
                "bid pipeline management",
                "bid success rate",
                "solicitation analysis",
                "manufacturing",
                "supply class analysis",
                "computer systems design and related services",
                "workflow automation",
                "supply class discovery",
                "b2b",
                "competitor tracking",
                "defense",
                "defense industry software",
                "ai opportunity matching",
                "price suggestions",
                "nsn opportunities",
                "bid analysis",
                "market insights",
                "computer & network security",
                "information technology & services",
                "mechanical or industrial engineering"
            ],
            "organization_revenue_printed": null,
            "organization_revenue": 0.0,
            "industries": [
                "defense & space"
            ],
            "secondary_industries": [],
            "snippets_loaded": true,
            "industry_tag_id": "5567e1097369641b5f810500",
            "industry_tag_hash": {
                "defense & space": "5567e1097369641b5f810500"
            },
            "retail_location_count": 0,
            "raw_address": "san francisco, california, united states",
            "street_address": "",
            "city": "San Francisco",
            "state": "California",
            "postal_code": null,
            "country": "United States",
            "owned_by_organization_id": null,
            "short_description": "Find solicitations. Bid. Win.\n\nHelping DoD manufacturers find the best solicitations and streamlining the bidding process. Get in touch and grow your business with SalesPatriot!",
            "suborganizations": [],
            "num_suborganizations": 0,
            "total_funding": null,
            "total_funding_printed": null,
            "latest_funding_round_date": null,
            "latest_funding_stage": null,
            "funding_events": [],
            "technology_names": [
                "CloudFlare Hosting",
                "Cloudflare DNS",
                "Gmail",
                "Google Apps",
                "Google Cloud Hosting",
                "Mobile Friendly"
            ],
            "current_technologies": [
                {
                "uid": "cloudflare_hosting",
                "name": "CloudFlare Hosting",
                "category": "Hosting"
                },
                {
                "uid": "cloudflare_dns",
                "name": "Cloudflare DNS",
                "category": "Domain Name Services"
                },
                {
                "uid": "gmail",
                "name": "Gmail",
                "category": "Email Providers"
                },
                {
                "uid": "google_apps",
                "name": "Google Apps",
                "category": "Other"
                },
                {
                "uid": "google_cloud_hosting",
                "name": "Google Cloud Hosting",
                "category": "Hosting"
                },
                {
                "uid": "mobile_friendly",
                "name": "Mobile Friendly",
                "category": "Other"
                }
            ],
            "org_chart_root_people_ids": [
                "6826c47692601d0001d93253"
            ],
            "org_chart_sector": null,
            "org_chart_removed": null,
            "org_chart_show_department_filter": null,
            "departmental_head_count": {
                "engineering": 7,
                "consulting": 1,
                "entrepreneurship": 2,
                "information_technology": 1,
                "sales": 1,
                "business_development": 1,
                "accounting": 0,
                "operations": 0,
                "finance": 0,
                "marketing": 0,
                "human_resources": 0,
                "legal": 0,
                "product_management": 0,
                "education": 0,
                "administrative": 0,
                "media_and_commmunication": 0,
                "arts_and_design": 0,
                "support": 0,
                "data_science": 0
            },
            "generic_org_insights": null
            }
        }
        ]

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await company_storage(pool, all_normalized_data, searched_orgs, bulk_enriched_orgs, single_enriched_orgs)

    asyncio.run(main())