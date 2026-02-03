import asyncio
import asyncpg
import logging
from storage_module.company_storage import company_storage
from storage_module.people_storage import people_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

async def main(
        pool: asyncpg.Pool,
        normalization_to_storage_queue: asyncio.Queue,
        enrichment_to_storage_queue:asyncio.Queue
):

    logger.info("Starting storage ...")

    while not normalization_to_storage_queue.empty() and not enrichment_to_storage_queue.empty():
        all_normalized_data = await normalization_to_storage_queue.get()
        enrichment_data = await enrichment_to_storage_queue.get()

    searched_orgs = enrichment_data.get('searched_orgs') 
    bulk_enriched_orgs = enrichment_data.get('bulk_enriched_orgs') 
    single_enriched_orgs = enrichment_data.get('single_enriched_orgs') 
    searched_people = enrichment_data.get('searched_people') 
    enriched_people = enrichment_data.get('enriched_people')

    org_ids = await company_storage(
        pool,
        all_normalized_data=all_normalized_data,
        searched_orgs=searched_orgs,
        bulk_enriched_orgs=bulk_enriched_orgs,
        single_enriched_orgs=single_enriched_orgs
    )

    await people_storage(
        searched_people=searched_people,
        enriched_people=enriched_people
    )

    return org_ids

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)

    DB_URL = os.getenv("MOCK_DATABASE_URL")

    async def demo():
        n2s = asyncio.Queue()
        e2s = asyncio.Queue()

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

        bulk_enriched_orgs = [
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
        ]

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

        await n2s.put(all_normalized_data)

        enriched_data = {'searched_orgs': [{'breadcrumbs': [{'label': 'Company Name', 'signal_field_name': 'q_organization_name', 'value': 'socratix ai', 'display_name': 'socratix ai'}], 'partial_results_only': False, 'has_join': False, 'disable_eu_prospecting': False, 'partial_results_limit': 10000, 'pagination': {'page': 1, 'per_page': 1, 'total_entries': 2, 'total_pages': 2}, 'accounts': [], 'organizations': [{'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'owned_by_organization_id': None, 'organization_revenue_printed': None, 'organization_revenue': 0.0, 'intent_strength': None, 'show_intent': True, 'has_intent_signal_account': False, 'intent_signal_account': None, 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}], 'model_ids': ['68642a1665412f000dc3bd13'], 'num_fetch_result': None, 'derived_params': {'recommendation_config_id': '68a2f508398f2a00015ce352'}}], 'bulk_enriched_orgs': [{'status': 'success', 'error_code': None, 'error_message': None, 'total_requested_domains': 1, 'unique_domains': 1, 'unique_enriched_records': 1, 'missing_records': 0, 'organizations': [{'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'industry': 'information technology & services', 'estimated_num_employees': 2, 'keywords': ['fraud', 'risk', 'ai agents', 'b2b', 'saas', 'software development', 'fraud detection', 'ai fraud detection', 'ai-powered analytics', 'fraud investigation automation', 'risk assessment', 'compliance support', 'ai for financial risk', 'fraud prevention tools', 'ai insights', 'risk team collaboration', 'risk management', 'ai automation', 'ai in compliance processes', 'risk team ai assistant', 'finance', 'management consulting services', 'risk analysis automation', 'ai coworker', 'automated fraud monitoring', 'computer software', 'information technology & services', 'computer & network security', 'financial services'], 'organization_revenue_printed': None, 'organization_revenue': 0.0, 'industries': ['information technology & services', 'computer software'], 'secondary_industries': ['computer software'], 'snippets_loaded': True, 'industry_tag_id': '5567cd4773696439b10b0000', 'industry_tag_hash': {'information technology & services': '5567cd4773696439b10b0000', 'computer software': '5567cd4e7369643b70010000'}, 'retail_location_count': 0, 'raw_address': 'san francisco, california, united states', 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'country': 'United States', 'postal_code': None, 'owned_by_organization_id': None, 'short_description': None, 'departmental_head_count': {'information_technology': 1, 'entrepreneurship': 2, 'accounting': 0, 'sales': 0, 'operations': 0, 'finance': 0, 'marketing': 0, 'human_resources': 0, 'legal': 0, 'engineering': 0, 'business_development': 0, 'product_management': 0, 'consulting': 0, 'education': 0, 'administrative': 0, 'media_and_commmunication': 0, 'arts_and_design': 0, 'support': 0, 'data_science': 0}, 'intent_strength': None, 'show_intent': False, 'has_intent_signal_account': False, 'intent_signal_account': None, 'generic_org_insights': None, 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}]}], 'single_enriched_orgs': [{'organization': {'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'industry': 'information technology & services', 'estimated_num_employees': 2, 'keywords': ['fraud', 'risk', 'ai agents', 'b2b', 'saas', 'software development', 'fraud detection', 'ai fraud detection', 'ai-powered analytics', 'fraud investigation automation', 'risk assessment', 'compliance support', 'ai for financial risk', 'fraud prevention tools', 'ai insights', 'risk team collaboration', 'risk management', 'ai automation', 'ai in compliance processes', 'risk team ai assistant', 'finance', 'management consulting services', 'risk analysis automation', 'ai coworker', 'automated fraud monitoring', 'computer software', 'information technology & services', 'computer & network security', 'financial services'], 'organization_revenue_printed': None, 'organization_revenue': 0.0, 'industries': ['information technology & services', 'computer software'], 'secondary_industries': ['computer software'], 'snippets_loaded': True, 'industry_tag_id': '5567cd4773696439b10b0000', 'industry_tag_hash': {'information technology & services': '5567cd4773696439b10b0000', 'computer software': '5567cd4e7369643b70010000'}, 'retail_location_count': 0, 'raw_address': 'san francisco, california, united states', 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'postal_code': None, 'country': 'United States', 'owned_by_organization_id': None, 'short_description': None, 'suborganizations': [], 'num_suborganizations': 0, 'total_funding': None, 'total_funding_printed': None, 'latest_funding_round_date': None, 'latest_funding_stage': None, 'funding_events': [], 'technology_names': [], 'current_technologies': [], 'org_chart_root_people_ids': ['6330da0b2164f6000155a8c6'], 'org_chart_sector': 'OrgChart::SectorHierarchy::Rules::IT', 'org_chart_removed': None, 'org_chart_show_department_filter': None, 'departmental_head_count': {'information_technology': 1, 'entrepreneurship': 2, 'accounting': 0, 'sales': 0, 'operations': 0, 'finance': 0, 'marketing': 0, 'human_resources': 0, 'legal': 0, 'engineering': 0, 'business_development': 0, 'product_management': 0, 'consulting': 0, 'education': 0, 'administrative': 0, 'media_and_commmunication': 0, 'arts_and_design': 0, 'support': 0, 'data_science': 0}, 'generic_org_insights': None}}], 'searched_people': {'breadcrumbs': [{'label': 'Include titles', 'signal_field_name': 'person_titles', 'value': 'ceo', 'display_name': 'ceo'}, {'label': 'Include titles', 'signal_field_name': 'person_titles', 'value': 'sales', 'display_name': 'sales'}, {'label': 'Include titles', 'signal_field_name': 'person_titles', 'value': 'founder', 'display_name': 'founder'}, {'label': 'Include people with similar titles', 'signal_field_name': 'include_similar_titles', 'value': True, 'display_name': 'Yes'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'owner', 'display_name': 'Owner'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'founder', 'display_name': 'Founder'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'c-suite', 'display_name': 'C-suite'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'partner', 'display_name': 'Partner'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'vp', 'display_name': 'Vp'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'head', 'display_name': 'Head'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'director', 'display_name': 'Director'}, {'label': 'Management Level', 'signal_field_name': 'person_seniorities', 'value': 'manager', 'display_name': 'Manager'}, {'label': 'Companies', 'signal_field_name': 'organization_ids', 'value': '68642a1665412f000dc3bd13', 'display_name': 'Socratix AI (YC S25)'}, {'label': 'Company Domains', 'signal_field_name': 'q_organization_domains_list', 'value': ['getsocratix.ai'], 'display_name': 'getsocratix.ai'}, {'label': 'Email Status', 'signal_field_name': 'contact_email_status', 'value': 'verified', 'display_name': 'Verified'}, {'label': 'Email Status', 'signal_field_name': 'contact_email_status', 'value': 'unverified', 'display_name': 'Unverified'}, {'label': 'Email Status', 'signal_field_name': 'contact_email_status', 'value': 'likely to engage', 'display_name': 'Likely to engage'}], 'partial_results_only': False, 'has_join': False, 'disable_eu_prospecting': False, 'partial_results_limit': 10000, 'pagination': {'page': 1, 'per_page': 10, 'total_entries': 2, 'total_pages': 1}, 'contacts': [], 'people': [{'id': '6330da0b2164f6000155a8c6', 'first_name': 'Riya', 'last_name': 'Jagetia', 'name': 'Riya Jagetia', 'linkedin_url': 'http://www.linkedin.com/in/riya-jagetia', 'title': 'Co-Founder & CEO', 'email_status': 'verified', 'photo_url': 'https://static.licdn.com/aero-v1/sc/h/9c8pery4andzj6ohjkjp54ma2', 'twitter_url': None, 'github_url': None, 'facebook_url': None, 'extrapolated_email_confidence': None, 'headline': 'Co-Founder & CEO at Socratix AI (YC S25) | ex-DoorDash, Unit21 | MIT CS | Building the next generation of fraud & risk tools', 'email': 'email_not_unlocked@domain.com', 'organization_id': '68642a1665412f000dc3bd13', 'employment_history': [{'_id': '68ffe74661676600015b3cc7', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68642a1665412f000dc3bd13', 'organization_name': 'Socratix AI', 'raw_address': None, 'start_date': '2025-06-01', 'title': 'Co-Founder & CEO', 'updated_at': None, 'id': '68ffe74661676600015b3cc7', 'key': '68ffe74661676600015b3cc7'}, {'_id': '68ffe74661676600015b3cc8', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '642e13d7b8a90400db1f98e7', 'organization_name': 'The House of Fraud', 'raw_address': None, 'start_date': '2024-01-01', 'title': 'Member', 'updated_at': None, 'id': '68ffe74661676600015b3cc8', 'key': '68ffe74661676600015b3cc8'}, {'_id': '68ffe74661676600015b3cc9', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2025-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fcb120742e9e60001561802', 'organization_name': 'DoorDash', 'raw_address': None, 'start_date': '2024-11-01', 'title': 'Fraud Platform Product Lead', 'updated_at': None, 'id': '68ffe74661676600015b3cc9', 'key': '68ffe74661676600015b3cc9'}, {'_id': '68ffe74661676600015b3cca', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-12-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5c9430160149c909492dd877', 'organization_name': 'Unit21', 'raw_address': None, 'start_date': '2023-01-01', 'title': 'AI/ ML Product Lead', 'updated_at': None, 'id': '68ffe74661676600015b3cca', 'key': '68ffe74661676600015b3cca'}, {'_id': '68ffe74661676600015b3ccb', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2022-10-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a11ff869702d77c2674502', 'organization_name': 'The D. E. Shaw Group', 'raw_address': None, 'start_date': '2020-09-01', 'title': 'Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccb', 'key': '68ffe74661676600015b3ccb'}, {'_id': '68ffe74661676600015b3ccc', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2020-09-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9ef1f4a6da98d9356f7f2a', 'organization_name': 'Cognite AS', 'raw_address': None, 'start_date': '2019-06-01', 'title': 'Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccc', 'key': '68ffe74661676600015b3ccc'}, {'_id': '68ffe74661676600015b3ccd', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2019-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9ef1f4a6da98d9356f7f2a', 'organization_name': 'Cognite AS', 'raw_address': None, 'start_date': '2019-01-01', 'title': 'Associate Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccd', 'key': '68ffe74661676600015b3ccd'}, {'_id': '68ffe74661676600015b3cce', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-12-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '628d1bf3c4d84900d88f9832', 'organization_name': 'Wayfair', 'raw_address': None, 'start_date': '2018-07-01', 'title': 'Supply Chain & Logistics Analyst (Co-Op)', 'updated_at': None, 'id': '68ffe74661676600015b3cce', 'key': '68ffe74661676600015b3cce'}, {'_id': '68ffe74661676600015b3ccf', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-08-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a1216169702d7fe6dfca02', 'organization_name': 'The Boston Consulting Group (BCG)', 'raw_address': None, 'start_date': '2017-06-01', 'title': 'Summer Associate', 'updated_at': None, 'id': '68ffe74661676600015b3ccf', 'key': '68ffe74661676600015b3ccf'}, {'_id': '68ffe74661676600015b3cd0', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2016-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5aa0e785a6da9840c1db96c1', 'organization_name': 'Bridgewater Associates', 'raw_address': None, 'start_date': '2016-06-01', 'title': 'Investment Associate Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd0', 'key': '68ffe74661676600015b3cd0'}, {'_id': '68ffe74661676600015b3cd1', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2015-08-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5da317fe12577d0001c60805', 'organization_name': 'VASCO Data Security', 'raw_address': None, 'start_date': '2015-06-01', 'title': 'Business Analytics Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd1', 'key': '68ffe74661676600015b3cd1'}, {'_id': '68ffe74661676600015b3cd2', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2014-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '65477f3e9ee7d7000141ca9b', 'organization_name': 'Case Western Reserve University/ Folio Photonics LLP', 'raw_address': None, 'start_date': '2010-08-01', 'title': 'Research Assistant/ Student Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd2', 'key': '68ffe74661676600015b3cd2'}], 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'country': 'United States', 'postal_code': None, 'formatted_address': 'San Francisco, CA, USA', 'time_zone': 'America/Los_Angeles', 'organization': {'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}, 'departments': ['c_suite'], 'subdepartments': ['executive', 'founder'], 'seniority': 'founder', 'functions': ['entrepreneurship'], 'intent_strength': None, 'show_intent': True, 'email_domain_catchall': False, 'revealed_for_current_team': True}, {'id': '66ee511a06e67b0001ebdb1c', 'first_name': 'Satya', 'last_name': 'Reddy', 'name': 'Satya Reddy', 'linkedin_url': 'http://www.linkedin.com/in/satya-vasanth', 'title': 'Co-Founder & CTO', 'email_status': 'verified', 'photo_url': 'https://media.licdn.com/dms/image/v2/D5603AQHKaBkDk2tHcA/profile-displayphoto-scale_200_200/B56ZlJlQa4I0AY-/0/1757876128130?e=2147483647&v=beta&t=IDddUprqNQLihUlhKPPjIO_FTlwnbkCbIEk8qkLfBN8', 'twitter_url': None, 'github_url': None, 'facebook_url': None, 'extrapolated_email_confidence': None, 'headline': 'Co-Founder & CTO - Socratix AI (YC S25) | Building AI co-workers for risk and fraud teams', 'email': 'email_not_unlocked@domain.com', 'organization_id': '68642a1665412f000dc3bd13', 'employment_history': [{'_id': '6907e6702e58a900010b4a33', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68642a1665412f000dc3bd13', 'organization_name': 'Socratix AI (YC S25)', 'raw_address': None, 'start_date': '2025-07-01', 'title': 'Co-Founder & CTO', 'updated_at': None, 'id': '6907e6702e58a900010b4a33', 'key': '6907e6702e58a900010b4a33'}, {'_id': '6907e6702e58a900010b4a34', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2025-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5569c124736964259c358a00', 'organization_name': 'Cruise', 'raw_address': None, 'start_date': '2024-06-01', 'title': 'Senior Software Engineer II - AI Foundations', 'updated_at': None, 'id': '6907e6702e58a900010b4a34', 'key': '6907e6702e58a900010b4a34'}, {'_id': '6907e6702e58a900010b4a35', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-05-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5b849427324d4453812f30dd', 'organization_name': 'Ghost Autonomy', 'raw_address': None, 'start_date': '2024-01-01', 'title': 'Machine Learning Services', 'updated_at': None, 'id': '6907e6702e58a900010b4a35', 'key': '6907e6702e58a900010b4a35'}, {'_id': '6907e6702e58a900010b4a36', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-01-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fca408962ba9b00f6d3c961', 'organization_name': 'LinkedIn', 'raw_address': None, 'start_date': '2021-07-01', 'title': 'Senior Software Engineer', 'updated_at': None, 'id': '6907e6702e58a900010b4a36', 'key': '6907e6702e58a900010b4a36'}, {'_id': '6907e6702e58a900010b4a37', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2021-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9f0b97a6da98d977ff1d67', 'organization_name': 'Helm.ai', 'raw_address': None, 'start_date': '2020-02-01', 'title': 'Research Engineer', 'updated_at': None, 'id': '6907e6702e58a900010b4a37', 'key': '6907e6702e58a900010b4a37'}, {'_id': '6907e6702e58a900010b4a38', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2020-02-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '556d540473696412619ae200', 'organization_name': 'Rubrik, Inc.', 'raw_address': None, 'start_date': '2019-02-01', 'title': 'Member of Technical Staff Data Platform', 'updated_at': None, 'id': '6907e6702e58a900010b4a38', 'key': '6907e6702e58a900010b4a38'}, {'_id': '6907e6702e58a900010b4a39', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-09-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fca408962ba9b00f6d3c961', 'organization_name': 'LinkedIn', 'raw_address': None, 'start_date': '2018-06-01', 'title': 'Big Data Engineering Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a39', 'key': '6907e6702e58a900010b4a39'}, {'_id': '6907e6702e58a900010b4a3a', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-03-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a1bf497468694f8f8aa90d', 'organization_name': 'UCLA Anderson School of Management', 'raw_address': None, 'start_date': '2018-01-01', 'title': 'Graduate Teaching Assistant', 'updated_at': None, 'id': '6907e6702e58a900010b4a3a', 'key': '6907e6702e58a900010b4a3a'}, {'_id': '6907e6702e58a900010b4a3b', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5e8cd98f0958f000ea1deec0', 'organization_name': 'Instart Logic Inc', 'raw_address': None, 'start_date': '2017-05-01', 'title': 'Data Platform Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a3b', 'key': '6907e6702e58a900010b4a3b'}, {'_id': '6907e6702e58a900010b4a3c', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2016-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9f506ea6da98d99781eff8', 'organization_name': 'Salesforce', 'raw_address': None, 'start_date': '2016-05-01', 'title': 'Software Developer Internship', 'updated_at': None, 'id': '6907e6702e58a900010b4a3c', 'key': '6907e6702e58a900010b4a3c'}, {'_id': '6907e6702e58a900010b4a3d', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2015-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5e8cd98f0958f000ea1deec0', 'organization_name': 'Instart Logic Inc', 'raw_address': None, 'start_date': '2015-05-01', 'title': 'Technical Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a3d', 'key': '6907e6702e58a900010b4a3d'}, {'_id': '6907e6702e58a900010b4a3e', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-04-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68d2417f52066f0014b81209', 'organization_name': 'Indian Institute of Technology, Hyderabad', 'raw_address': None, 'start_date': '2014-08-01', 'title': 'Undergraduate Teaching Assistant', 'updated_at': None, 'id': '6907e6702e58a900010b4a3e', 'key': '6907e6702e58a900010b4a3e'}], 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'country': 'United States', 'postal_code': None, 'formatted_address': 'San Francisco, CA, USA', 'time_zone': 'America/Los_Angeles', 'organization': {'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}, 'departments': ['c_suite', 'master_engineering_technical'], 'subdepartments': ['founder', 'information_technology_executive', 'engineering_technical', 'technology_operations'], 'seniority': 'founder', 'functions': ['information_technology', 'entrepreneurship'], 'intent_strength': None, 'show_intent': True, 'email_domain_catchall': False, 'revealed_for_current_team': True}], 'model_ids': ['6330da0b2164f6000155a8c6', '66ee511a06e67b0001ebdb1c'], 'num_fetch_result': None, 'derived_params': {'recommendation_config_id': '68a2f518398f2a00015ce36b'}}, 'enriched_people': [{'person': {'id': '6330da0b2164f6000155a8c6', 'first_name': 'Riya', 'last_name': 'Jagetia', 'name': 'Riya Jagetia', 'linkedin_url': 'http://www.linkedin.com/in/riya-jagetia', 'title': 'Co-Founder & CEO', 'email_status': 'verified', 'photo_url': 'https://static.licdn.com/aero-v1/sc/h/9c8pery4andzj6ohjkjp54ma2', 'twitter_url': None, 'github_url': None, 'facebook_url': None, 'extrapolated_email_confidence': None, 'headline': 'Co-Founder & CEO at Socratix AI (YC S25) | ex-DoorDash, Unit21 | MIT CS | Building the next generation of fraud & risk tools', 'email': 'riya@getsocratix.ai', 'organization_id': '68642a1665412f000dc3bd13', 'employment_history': [{'_id': '68ffe74661676600015b3cc7', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68642a1665412f000dc3bd13', 'organization_name': 'Socratix AI', 'raw_address': None, 'start_date': '2025-06-01', 'title': 'Co-Founder & CEO', 'updated_at': None, 'id': '68ffe74661676600015b3cc7', 'key': '68ffe74661676600015b3cc7'}, {'_id': '68ffe74661676600015b3cc8', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '642e13d7b8a90400db1f98e7', 'organization_name': 'The House of Fraud', 'raw_address': None, 'start_date': '2024-01-01', 'title': 'Member', 'updated_at': None, 'id': '68ffe74661676600015b3cc8', 'key': '68ffe74661676600015b3cc8'}, {'_id': '68ffe74661676600015b3cc9', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2025-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fcb120742e9e60001561802', 'organization_name': 'DoorDash', 'raw_address': None, 'start_date': '2024-11-01', 'title': 'Fraud Platform Product Lead', 'updated_at': None, 'id': '68ffe74661676600015b3cc9', 'key': '68ffe74661676600015b3cc9'}, {'_id': '68ffe74661676600015b3cca', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-12-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5c9430160149c909492dd877', 'organization_name': 'Unit21', 'raw_address': None, 'start_date': '2023-01-01', 'title': 'AI/ ML Product Lead', 'updated_at': None, 'id': '68ffe74661676600015b3cca', 'key': '68ffe74661676600015b3cca'}, {'_id': '68ffe74661676600015b3ccb', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2022-10-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a11ff869702d77c2674502', 'organization_name': 'The D. E. Shaw Group', 'raw_address': None, 'start_date': '2020-09-01', 'title': 'Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccb', 'key': '68ffe74661676600015b3ccb'}, {'_id': '68ffe74661676600015b3ccc', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2020-09-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9ef1f4a6da98d9356f7f2a', 'organization_name': 'Cognite AS', 'raw_address': None, 'start_date': '2019-06-01', 'title': 'Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccc', 'key': '68ffe74661676600015b3ccc'}, {'_id': '68ffe74661676600015b3ccd', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2019-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9ef1f4a6da98d9356f7f2a', 'organization_name': 'Cognite AS', 'raw_address': None, 'start_date': '2019-01-01', 'title': 'Associate Product Manager', 'updated_at': None, 'id': '68ffe74661676600015b3ccd', 'key': '68ffe74661676600015b3ccd'}, {'_id': '68ffe74661676600015b3cce', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-12-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '628d1bf3c4d84900d88f9832', 'organization_name': 'Wayfair', 'raw_address': None, 'start_date': '2018-07-01', 'title': 'Supply Chain & Logistics Analyst (Co-Op)', 'updated_at': None, 'id': '68ffe74661676600015b3cce', 'key': '68ffe74661676600015b3cce'}, {'_id': '68ffe74661676600015b3ccf', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-08-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a1216169702d7fe6dfca02', 'organization_name': 'The Boston Consulting Group (BCG)', 'raw_address': None, 'start_date': '2017-06-01', 'title': 'Summer Associate', 'updated_at': None, 'id': '68ffe74661676600015b3ccf', 'key': '68ffe74661676600015b3ccf'}, {'_id': '68ffe74661676600015b3cd0', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2016-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5aa0e785a6da9840c1db96c1', 'organization_name': 'Bridgewater Associates', 'raw_address': None, 'start_date': '2016-06-01', 'title': 'Investment Associate Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd0', 'key': '68ffe74661676600015b3cd0'}, {'_id': '68ffe74661676600015b3cd1', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2015-08-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5da317fe12577d0001c60805', 'organization_name': 'VASCO Data Security', 'raw_address': None, 'start_date': '2015-06-01', 'title': 'Business Analytics Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd1', 'key': '68ffe74661676600015b3cd1'}, {'_id': '68ffe74661676600015b3cd2', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2014-06-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '65477f3e9ee7d7000141ca9b', 'organization_name': 'Case Western Reserve University/ Folio Photonics LLP', 'raw_address': None, 'start_date': '2010-08-01', 'title': 'Research Assistant/ Student Intern', 'updated_at': None, 'id': '68ffe74661676600015b3cd2', 'key': '68ffe74661676600015b3cd2'}], 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'country': 'United States', 'postal_code': None, 'formatted_address': 'San Francisco, CA, USA', 'time_zone': 'America/Los_Angeles', 'organization': {'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'industry': 'information technology & services', 'estimated_num_employees': 2, 'keywords': ['fraud', 'risk', 'ai agents', 'b2b', 'saas', 'software development', 'fraud detection', 'ai fraud detection', 'ai-powered analytics', 'fraud investigation automation', 'risk assessment', 'compliance support', 'ai for financial risk', 'fraud prevention tools', 'ai insights', 'risk team collaboration', 'risk management', 'ai automation', 'ai in compliance processes', 'risk team ai assistant', 'finance', 'management consulting services', 'risk analysis automation', 'ai coworker', 'automated fraud monitoring', 'computer software', 'information technology & services', 'computer & network security', 'financial services'], 'organization_revenue_printed': None, 'organization_revenue': 0.0, 'industries': ['information technology & services', 'computer software'], 'secondary_industries': ['computer software'], 'snippets_loaded': True, 'industry_tag_id': '5567cd4773696439b10b0000', 'industry_tag_hash': {'information technology & services': '5567cd4773696439b10b0000', 'computer software': '5567cd4e7369643b70010000'}, 'retail_location_count': 0, 'raw_address': 'san francisco, california, united states', 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'postal_code': None, 'country': 'United States', 'owned_by_organization_id': None, 'short_description': None, 'suborganizations': [], 'num_suborganizations': 0, 'total_funding': None, 'total_funding_printed': None, 'latest_funding_round_date': None, 'latest_funding_stage': None, 'funding_events': [], 'technology_names': [], 'current_technologies': [], 'org_chart_root_people_ids': ['6330da0b2164f6000155a8c6'], 'org_chart_sector': 'OrgChart::SectorHierarchy::Rules::IT', 'org_chart_removed': None, 'org_chart_show_department_filter': None, 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}, 'intent_strength': None, 'show_intent': False, 'email_domain_catchall': False, 'revealed_for_current_team': True, 'personal_emails': [], 'departments': ['c_suite'], 'subdepartments': ['executive', 'founder'], 'functions': ['entrepreneurship'], 'seniority': 'founder'}}, {'person': {'id': '66ee511a06e67b0001ebdb1c', 'first_name': 'Satya', 'last_name': 'Reddy', 'name': 'Satya Reddy', 'linkedin_url': 'http://www.linkedin.com/in/satya-vasanth', 'title': 'Co-Founder & CTO', 'email_status': 'verified', 'photo_url': 'https://media.licdn.com/dms/image/v2/D5603AQHKaBkDk2tHcA/profile-displayphoto-scale_200_200/B56ZlJlQa4I0AY-/0/1757876128130?e=2147483647&v=beta&t=IDddUprqNQLihUlhKPPjIO_FTlwnbkCbIEk8qkLfBN8', 'twitter_url': None, 'github_url': None, 'facebook_url': None, 'extrapolated_email_confidence': None, 'headline': 'Co-Founder & CTO - Socratix AI (YC S25) | Building AI co-workers for risk and fraud teams', 'email': 'satya@getsocratix.ai', 'organization_id': '68642a1665412f000dc3bd13', 'employment_history': [{'_id': '6907e6702e58a900010b4a33', 'created_at': None, 'current': True, 'degree': None, 'description': None, 'emails': None, 'end_date': None, 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68642a1665412f000dc3bd13', 'organization_name': 'Socratix AI (YC S25)', 'raw_address': None, 'start_date': '2025-07-01', 'title': 'Co-Founder & CTO', 'updated_at': None, 'id': '6907e6702e58a900010b4a33', 'key': '6907e6702e58a900010b4a33'}, {'_id': '6907e6702e58a900010b4a34', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2025-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5569c124736964259c358a00', 'organization_name': 'Cruise', 'raw_address': None, 'start_date': '2024-06-01', 'title': 'Senior Software Engineer II - AI Foundations', 'updated_at': None, 'id': '6907e6702e58a900010b4a34', 'key': '6907e6702e58a900010b4a34'}, {'_id': '6907e6702e58a900010b4a35', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-05-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5b849427324d4453812f30dd', 'organization_name': 'Ghost Autonomy', 'raw_address': None, 'start_date': '2024-01-01', 'title': 'Machine Learning Services', 'updated_at': None, 'id': '6907e6702e58a900010b4a35', 'key': '6907e6702e58a900010b4a35'}, {'_id': '6907e6702e58a900010b4a36', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2024-01-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fca408962ba9b00f6d3c961', 'organization_name': 'LinkedIn', 'raw_address': None, 'start_date': '2021-07-01', 'title': 'Senior Software Engineer', 'updated_at': None, 'id': '6907e6702e58a900010b4a36', 'key': '6907e6702e58a900010b4a36'}, {'_id': '6907e6702e58a900010b4a37', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2021-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9f0b97a6da98d977ff1d67', 'organization_name': 'Helm.ai', 'raw_address': None, 'start_date': '2020-02-01', 'title': 'Research Engineer', 'updated_at': None, 'id': '6907e6702e58a900010b4a37', 'key': '6907e6702e58a900010b4a37'}, {'_id': '6907e6702e58a900010b4a38', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2020-02-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '556d540473696412619ae200', 'organization_name': 'Rubrik, Inc.', 'raw_address': None, 'start_date': '2019-02-01', 'title': 'Member of Technical Staff Data Platform', 'updated_at': None, 'id': '6907e6702e58a900010b4a38', 'key': '6907e6702e58a900010b4a38'}, {'_id': '6907e6702e58a900010b4a39', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-09-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5fca408962ba9b00f6d3c961', 'organization_name': 'LinkedIn', 'raw_address': None, 'start_date': '2018-06-01', 'title': 'Big Data Engineering Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a39', 'key': '6907e6702e58a900010b4a39'}, {'_id': '6907e6702e58a900010b4a3a', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2018-03-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '54a1bf497468694f8f8aa90d', 'organization_name': 'UCLA Anderson School of Management', 'raw_address': None, 'start_date': '2018-01-01', 'title': 'Graduate Teaching Assistant', 'updated_at': None, 'id': '6907e6702e58a900010b4a3a', 'key': '6907e6702e58a900010b4a3a'}, {'_id': '6907e6702e58a900010b4a3b', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5e8cd98f0958f000ea1deec0', 'organization_name': 'Instart Logic Inc', 'raw_address': None, 'start_date': '2017-05-01', 'title': 'Data Platform Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a3b', 'key': '6907e6702e58a900010b4a3b'}, {'_id': '6907e6702e58a900010b4a3c', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2016-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5a9f506ea6da98d99781eff8', 'organization_name': 'Salesforce', 'raw_address': None, 'start_date': '2016-05-01', 'title': 'Software Developer Internship', 'updated_at': None, 'id': '6907e6702e58a900010b4a3c', 'key': '6907e6702e58a900010b4a3c'}, {'_id': '6907e6702e58a900010b4a3d', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2015-07-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '5e8cd98f0958f000ea1deec0', 'organization_name': 'Instart Logic Inc', 'raw_address': None, 'start_date': '2015-05-01', 'title': 'Technical Intern', 'updated_at': None, 'id': '6907e6702e58a900010b4a3d', 'key': '6907e6702e58a900010b4a3d'}, {'_id': '6907e6702e58a900010b4a3e', 'created_at': None, 'current': False, 'degree': None, 'description': None, 'emails': None, 'end_date': '2017-04-01', 'grade_level': None, 'kind': None, 'major': None, 'organization_id': '68d2417f52066f0014b81209', 'organization_name': 'Indian Institute of Technology, Hyderabad', 'raw_address': None, 'start_date': '2014-08-01', 'title': 'Undergraduate Teaching Assistant', 'updated_at': None, 'id': '6907e6702e58a900010b4a3e', 'key': '6907e6702e58a900010b4a3e'}], 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'country': 'United States', 'postal_code': None, 'formatted_address': 'San Francisco, CA, USA', 'time_zone': 'America/Los_Angeles', 'organization': {'id': '68642a1665412f000dc3bd13', 'name': 'Socratix AI (YC S25)', 'website_url': 'http://www.getsocratix.ai', 'blog_url': None, 'angellist_url': None, 'linkedin_url': 'http://www.linkedin.com/company/socratix-ai', 'twitter_url': None, 'facebook_url': None, 'primary_phone': {}, 'languages': [], 'alexa_ranking': None, 'phone': None, 'linkedin_uid': '107129095', 'founded_year': None, 'publicly_traded_symbol': None, 'publicly_traded_exchange': None, 'logo_url': 'https://zenprospect-production.s3.amazonaws.com/uploads/pictures/68e4f2b580f9f60001e06412/picture', 'crunchbase_url': None, 'primary_domain': 'getsocratix.ai', 'sic_codes': ['7375'], 'naics_codes': ['54161'], 'industry': 'information technology & services', 'estimated_num_employees': 2, 'keywords': ['fraud', 'risk', 'ai agents', 'b2b', 'saas', 'software development', 'fraud detection', 'ai fraud detection', 'ai-powered analytics', 'fraud investigation automation', 'risk assessment', 'compliance support', 'ai for financial risk', 'fraud prevention tools', 'ai insights', 'risk team collaboration', 'risk management', 'ai automation', 'ai in compliance processes', 'risk team ai assistant', 'finance', 'management consulting services', 'risk analysis automation', 'ai coworker', 'automated fraud monitoring', 'computer software', 'information technology & services', 'computer & network security', 'financial services'], 'organization_revenue_printed': None, 'organization_revenue': 0.0, 'industries': ['information technology & services', 'computer software'], 'secondary_industries': ['computer software'], 'snippets_loaded': True, 'industry_tag_id': '5567cd4773696439b10b0000', 'industry_tag_hash': {'information technology & services': '5567cd4773696439b10b0000', 'computer software': '5567cd4e7369643b70010000'}, 'retail_location_count': 0, 'raw_address': 'san francisco, california, united states', 'street_address': '', 'city': 'San Francisco', 'state': 'California', 'postal_code': None, 'country': 'United States', 'owned_by_organization_id': None, 'short_description': None, 'suborganizations': [], 'num_suborganizations': 0, 'total_funding': None, 'total_funding_printed': None, 'latest_funding_round_date': None, 'latest_funding_stage': None, 'funding_events': [], 'technology_names': [], 'current_technologies': [], 'org_chart_root_people_ids': ['6330da0b2164f6000155a8c6'], 'org_chart_sector': 'OrgChart::SectorHierarchy::Rules::IT', 'org_chart_removed': None, 'org_chart_show_department_filter': None, 'organization_headcount_six_month_growth': None, 'organization_headcount_twelve_month_growth': None, 'organization_headcount_twenty_four_month_growth': None}, 'intent_strength': None, 'show_intent': False, 'email_domain_catchall': False, 'revealed_for_current_team': True, 'personal_emails': [], 'departments': ['c_suite', 'master_engineering_technical'], 'subdepartments': ['founder', 'information_technology_executive', 'engineering_technical', 'technology_operations'], 'functions': ['information_technology', 'entrepreneurship'], 'seniority': 'founder'}}]}
        await e2s.put(enriched_data)

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await main(pool, n2s, e2s)

    asyncio.run(demo())