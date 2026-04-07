"""
The suite covers 20 diverse real-world scenarios, ensuring robust performance under different conditions:

Product-Led (Funding): ManageMy (Series B).
Product-Led (Hiring): Darwin AI (Software Engineering).
Agency/Outstaffing: QIT Software (Data Engineer).
Messy Names: Global Solutions Inc. - Leading provider of enterprise ERP (Agency).
Stealth Mode: Stealth AI (Vague descriptions).
Traditional/Non-Tech: Baker & Sons Logistics hiring tech talent.
Messy Location Names: Creative Minds Marketing (Gurgaon Branch).
Biotech/Healthcare: BioGenomix research (Seed).
Informal Agency: AppMasterZ LLC.
Specialized Tools: DataViz.ai.
Legacy Modernization: Legacy Banking Systems Refactored.
Consumer Products: The Social App.
Niche Consultancy: DevOps Experts UK.
University Spin-offs: University Spin-off alpha.
Enterprise Platforms: QuickHire.com (Series C).
"""
import asyncio
import json
import os
import sys
import logging
import re
import aiofiles

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outreach_module.ai_email_generation import call_gemini_api
from utils.prompts.email_generation_prompt import get_email_generation_prompt

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 20 Diverse Test Cases
TEST_CASES = [
    {
        "name": "Standard SaaS (Product-Led, Funding)",
        "company_name": "ManageMy",
        "description": "ManageMy is a SaaS technology company based in Charlotte, North Carolina. They specialize in an AI-driven digital platform designed for insurance carriers to streamline buying, underwriting, servicing, and claims.",
        "trigger_type": "funding",
        "funding_round": "Series B",
        "first_name": "Jane",
        "painpoints": ["Scaling operational throughput", "Maintaining QA standards during rapid growth"]
    },
    {
        "name": "Ad-Tech AI (Product-Led, Hiring)",
        "company_name": "Darwin AI",
        "description": "Darwin AI specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. They focus on data-driven creative testing and analytics.",
        "trigger_type": "hiring",
        "hiring_area": "Software Engineering",
        "first_name": "Mark",
        "painpoints": ["Internal roadmap acceleration", "Building custom AI models for creative analysis"]
    },
    {
        "name": "Outstaffing/Dev Shop (Agency, Hiring)",
        "company_name": "QIT Software",
        "description": "QIT Software is a software development company based in Plano, Texas. We specialize in crafting bespoke web and mobile solutions and help global businesses scale their engineering teams via IT Staff Augmentation.",
        "trigger_type": "hiring",
        "hiring_area": "Data Engineer",
        "first_name": "Yegor",
        "painpoints": ["Bench capacity", "Supporting client delivery for AI/ML projects"]
    },
    {
        "name": "Messy Name / Traditional ERP (Agency, Hiring)",
        "company_name": "Global Solutions Inc. - Leading provider of enterprise ERP and legacy modernization",
        "description": "We are a global leader in ERP implementation and legacy system modernization. We provide dedicated development teams for large scale enterprise migrations and cloud transitions.",
        "trigger_type": "hiring",
        "hiring_area": "Backend Developer",
        "first_name": "Robert",
        "painpoints": ["Legacy code refactoring", "Slow release cycles for enterprise clients"]
    },
    {
        "name": "Stealth Mode (Vague, Funding)",
        "company_name": "Stealth AI",
        "description": "We are building the next generation of generative AI for the enterprise. Currently in stealth mode with a focus on privacy and security.",
        "trigger_type": "funding",
        "funding_round": "Seed",
        "first_name": "Alex",
        "painpoints": ["Model training at scale", "Data privacy compliance"]
    },
    {
        "name": "Traditional Logistics (Non-Tech, Hiring)",
        "company_name": "Baker & Sons Logistics & Distribution Services",
        "description": "Family-owned logistics company since 1954. We are recently investing in a new digital department to automate our warehouse tracking systems.",
        "trigger_type": "hiring",
        "hiring_area": "Fullstack Developer",
        "first_name": "Tom",
        "painpoints": ["Warehouse automation", "Legacy database migration"]
    },
    {
        "name": "FinTech Startup (Product, Funding)",
        "company_name": "FinTechly.io",
        "description": "A modern platform for cross-border payments and currency exchange for SMBs.",
        "trigger_type": "funding",
        "funding_round": "Series A",
        "first_name": "Sarah",
        "painpoints": ["Regulatory compliance", "Real-time fraud detection"]
    },
    {
        "name": "Messy Location Name (Agency, Hiring)",
        "company_name": "Creative Minds Marketing & PR Agency (Gurgaon Branch)",
        "description": "Digital marketing and PR services for global brands. We are expanding our tech team to build custom campaign tracking tools.",
        "trigger_type": "hiring",
        "hiring_area": "Frontend Developer",
        "first_name": "Anjali",
        "painpoints": ["Campaign tracking automation", "Dashboard UI/UX"]
    },
    {
        "name": "Biotech (Healthcare, Funding)",
        "company_name": "BioGenomix research lab",
        "description": "BioGenomix is a clinical-stage biotechnology company focused on developing gene therapies for rare diseases using AI for protein folding analysis.",
        "trigger_type": "funding",
        "funding_round": "Grant",
        "first_name": "Dr. Miller",
        "painpoints": ["Genomic data processing", "AI model accuracy for diagnostics"]
    },
    {
        "name": "Informal Agency Name (Agency, Hiring)",
        "company_name": "AppMasterZ LLC",
        "description": "We build cool apps for startups. Web, mobile, whatever you need. We are a small but mighty team of hackers and designers.",
        "trigger_type": "hiring",
        "hiring_area": "Mobile Developer (React Native)",
        "first_name": "Dave",
        "painpoints": ["Fast-paced delivery", "Cross-platform app performance"]
    },
    {
        "name": "Specialized Data Tool (Product, Funding)",
        "company_name": "DataViz.ai",
        "description": "The easiest way to visualize your complex data streams in real-time. No-code dashboards for everyone.",
        "trigger_type": "funding",
        "funding_round": "Post-Seed",
        "first_name": "Elena",
        "painpoints": ["Real-time data ingestion", "Custom visualization features"]
    },
    {
        "name": "Legacy Tech Agency (Agency, Hiring)",
        "company_name": "Legacy Banking Systems Refactored",
        "description": "We specialize in Cobol to Java migrations and mainframe modernization for mid-sized regional banks.",
        "trigger_type": "hiring",
        "hiring_area": "Java Developer",
        "first_name": "George",
        "painpoints": ["Legacy system bottlenecks", "Modernizing core banking features"]
    },
    {
        "name": "EcoTech (IoT, Hiring)",
        "company_name": "EcoClean - Sustainable Tech Solutions for Cities",
        "description": "EcoClean builds smart waste management sensors and software for sustainable city planning.",
        "trigger_type": "hiring",
        "hiring_area": "Python/IoT Engineer",
        "first_name": "Lisa",
        "painpoints": ["Sensor data optimization", "Real-time fleet routing"]
    },
    {
        "name": "Consumer Tech (Product, Funding)",
        "company_name": "The Social App",
        "description": "A new social media platform focused on mental health and community support.",
        "trigger_type": "funding",
        "funding_round": "Pre-Seed",
        "first_name": "Sam",
        "painpoints": ["User growth scaling", "Content moderation AI"]
    },
    {
        "name": "DevOps Consultancy (Consultancy, Hiring)",
        "company_name": "DevOps Experts UK",
        "description": "We provide hands-on DevOps and SRE consulting for companies migrating to Kubernetes.",
        "trigger_type": "hiring",
        "hiring_area": "Kubernetes Specialist",
        "first_name": "John",
        "painpoints": ["Cloud cost optimization", "Pipeline automation"]
    },
    {
        "name": "Spin-off (Vague AI, Hiring)",
        "company_name": "University Spin-off alpha",
        "description": "A laboratory-born project commercializing new research into unsupervised learning for robotics.",
        "trigger_type": "hiring",
        "hiring_area": "Robotics Engineer",
        "first_name": "Prof. Chen",
        "painpoints": ["Prototype development", "Data collection for training"]
    },
    {
        "name": "HR Tech (Product, Funding)",
        "company_name": "QuickHire.com",
        "description": "AI-powered hiring platform that matches companies with the top 1% of remote developers.",
        "trigger_type": "funding",
        "funding_round": "Series C",
        "first_name": "Karen",
        "painpoints": ["Scaling international outreach", "Improving matching algorithms"]
    },
    {
        "name": "Marketing Cloud (Product, Hiring)",
        "company_name": "AdFlow Cloud Systems",
        "description": "Cloud-based ad management platform for high-volume advertisers looking for transparency and better ROI.",
        "trigger_type": "hiring",
        "hiring_area": "Fullstack Engineer",
        "first_name": "James",
        "painpoints": ["Ad spend tracking", "Reporting performance at scale"]
    },
    {
        "name": "E-commerce SaaS (Product, Funding)",
        "company_name": "ShopBoost AI",
        "description": "Empowering Shopify merchants with AI-driven product recommendations and personalized marketing.",
        "trigger_type": "funding",
        "funding_round": "Venture",
        "first_name": "Chloe",
        "painpoints": ["Personalization engine latency", "Merchant onboarding automation"]
    },
    {
        "name": "Cybersecurity (Product, Hiring)",
        "company_name": "SecureLink AI",
        "description": "Next-gen endpoint protection platform using autonomous AI agents to detect and neutralize threats.",
        "trigger_type": "hiring",
        "hiring_area": "Security Researcher",
        "first_name": "Peter",
        "painpoints": ["Threat detection false positives", "Automating real-time response scripts"]
    }
]

async def run_test_suite():
    print("="*80)
    print(f"AI EMAIL GENERATION EXTENSIVE TEST SUITE - {len(TEST_CASES)} CASES")
    print("="*80)
    all_results = []
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n[RUNNING TEST {i}/{len(TEST_CASES)}]: {case['name']}")
        print(f"Trigger: {case.get('trigger_type').upper()} | Target: {case.get('hiring_area') or case.get('funding_round')}")
        
        prompt = get_email_generation_prompt(
            company_description=case['description'],
            first_name=case['first_name'],
            company_name=case['company_name'],
            trigger_type=case['trigger_type'],
            sequence_number=1, # Initial outreach
            funding_round=case.get('funding_round'),
            hiring_area=case.get('hiring_area'),
            painpoints=case['painpoints']
        )
        
        try:
            response = await call_gemini_api(prompt)
            if not response:
                print("FAILED: No response from API.")
                continue
                
            text = response.candidates[0].content.parts[0].text
            email_data = json.loads(text)
            
            subject = email_data.get('subject', '')
            
            # Simple but robust HTML tag removal
            clean_body = re.sub(r'<(p|br|li|div|h1|h2|h3)\b[^>]*>', '\n', email_data.get('content', ''))
            clean_body = re.sub(r'<[^>]+>', '', clean_body)
            # Normalize whitespace and newlines
            clean_body = re.sub(r'\n+', '\n', clean_body).strip()
            print(f"BODY: {clean_body}")
            print("-" * 80)
            
            # Combine test case properties with the email result
            result_item = case.copy()
            result_item["email_subject"] = subject
            result_item["email_body"] = clean_body
            all_results.append(result_item)

        except Exception as e:
            logger.error(f"Test Case '{case['name']}' failed: {str(e)}")
            
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)

    async with aiofiles.open('emails_for_antony.json', 'w') as file:
        await file.write(json.dumps(all_results, indent=2))

if __name__ == "__main__":
    asyncio.run(run_test_suite())
