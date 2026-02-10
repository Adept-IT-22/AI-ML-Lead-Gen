import asyncio
from scoring_module.icp_scoring import ICPScorer
from utils.icp import icp
import json

company_data = {
    "annual_revenue":None,
    "apollo_id":"64f197bd09642d00ba8f3a76",
    "category_breakdown":None,
    "city":"Paris",
    "company_data_source":"funding",
    "contacted_status":"uncontacted",
    "contacted_status_precedence":0,
    "country":"France",
    "created_at":"Mon, 08 Sep 2025 07:43:41 GMT",
    "estimated_num_employees":3,
    "founded_year":2016,
    "icp_score":"54.4",
    "id":10,
    "industries":["public relations & communications","marketing & advertising"],
    "interpretation":"LOW - Minimal alignment",
    "keywords":["public relations & communications services","content distribution","media relations","cross-media campaigns","content marketing","public relations","press campaigns","multichannel marketing","campaign management","tv and radio campaigns","prestige press","media partnerships","brand content","marketing and branding","content creation","social media marketing","brand visibility","premium media diffusion","digital marketing","prestigious media","media planning","seo/sea","website creation","multimedia content","digital marketing and content creation","brand storytelling","branding strategy","media buying","audience targeting","multimedia content strategy","media impact measurement","media and advertising","regional and national campaigns","communication strategy","digital strategy","media collaboration","influencer relations","press relations","public relations and communications","multilingual media partnerships","campaign analytics","cross-channel diffusion","b2b","consulting","services","public relations agencies","branding","web development","online presence","brand awareness","public relations & communications","marketing & advertising","consumer internet","consumers","internet","information technology & services","marketing"],
    "latest_funding_amount":None,
    "latest_funding_currency":None,
    "latest_funding_round":None,
    "market_cap":None,
    "name":"Koah Média",
    "notes":None,
    "organization_headcount_six_month_growth":None,
    "organization_headcount_twelve_month_growth":None,
    "people":[],
    "phone":None,
    "short_description":"Koah Média specializes in AI-native advertising solutions...",
    "source_link":None,
    "state":"Ile-de-France",
    "status":"lead",
    "technology_names":["Facebook Custom Audiences","Facebook Login (Connect)","Facebook Widget","Google Font API","Google Tag Manager","Mobile Friendly","Woo Commerce","WordPress.org"],
    "top_matches":"[[\"lower_transcription_and_reporting\", \"0.0599\"], [\"higher_domain_specific_applications\", \"0.0419\"], [\"higher_strategic_decision_making\", \"0.0367\"]]",
    "total_funding":None,
    "updated_at":"Mon, 08 Sep 2025 07:43:41 GMT",
    "website_url":"http://www.koahmedia.co"
}

async def main():
    name = company_data.get('name')
    founded_year = company_data.get('founded_year')
    employee_count = company_data.get('estimated_num_employees')
    funding_stage = company_data.get('latest_funding_round')
    keywords = company_data.get('keywords')
    people = company_data.get('people', [])
    phone = company_data.get('phone', '')
    # Handle people list for linkedin extraction like in main code
    linkedin = [p.get('linkedin_url', '') for p in people][0] if people and people[0].get('linkedin_url') else None
    
    website = company_data.get('website_url', '')
    country = company_data.get('country', '')

    scorer = ICPScorer(icp, name, founded_year, employee_count, 
                       funding_stage, keywords, people, phone, 
                       linkedin, website, country)

    await scorer.log_scoring_start(name)
    result = await scorer.calculate_total_score()
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
