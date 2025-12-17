import json
import aiofiles
import asyncio
import logging
from services.db_service import *
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def main(
        pool: asyncpg.Pool,
        ingestion_to_normalization_queue: asyncio.Queue, 
        normalization_to_enrichment_queue: asyncio.Queue,
        normalization_to_storage_queue: asyncio.Queue
        )->asyncio.Queue: 

    logger.info("Normalizing ingested data....")
    all_normalized_data = []

    while not ingestion_to_normalization_queue.empty():
        name, data = await ingestion_to_normalization_queue.get()
        logger.info(f"Fetched data from {name}. Queue size is now: {ingestion_to_normalization_queue.qsize()}")

        # ========== Normalize data ===============
        data_type = data.get("type")

        # Step 1: Normalize
        if data_type == "event":
            normalized_data = await normalize_event_data(data)
        elif data_type == "funding":
            normalized_data = await normalize_funding_data(data)
        elif data_type == "hiring":
            normalized_data = await normalize_hiring_data(data)
        else:
            logger.warning(f"Unknown data type: {data_type}")
            return

        # Step 2: Insert master (one row per dataset)
        for i, normalized_link in enumerate(normalized_data.get("link")):
            normalized_master_data_to_store = [
                normalized_data.get("type", ""),
                normalized_data.get("source")[0] if normalized_data.get("source") else "",
                normalized_link,
                normalized_data.get("title")[i] if normalized_data.get("title") and i < len(normalized_data.get("title", [])) else None,
                normalized_data.get("city")[i] if normalized_data.get("city") and i < len(normalized_data.get("city", [])) else None,
                normalized_data.get("country")[i] if normalized_data.get("country") and i < len(normalized_data.get("country", [])) else None,
                normalized_data.get("tags")[i] if normalized_data.get("tags") and i < len(normalized_data.get("tags", [])) else []
            ]
            data_is_in_db = await is_data_in_db(pool, normalized_link)
            if data_is_in_db:
                continue
            master_id = await store_in_normalized_master(normalized_master_data_to_store, pool)

            # Step 3: Insert children
            if data_type == "event":
                event_data_to_store = [
                    master_id,
                    normalized_data.get("event_id")[i] if normalized_data.get("event_id") and i < len(normalized_data.get("event_id", [])) else None,
                    normalized_data.get("event_summary")[i] if normalized_data.get("event_summary") and i < len(normalized_data.get("event_summary", [])) else None,
                    normalized_data.get("event_is_online")[i] if normalized_data.get("event_is_online") and i < len(normalized_data.get("event_is_online", [])) else None,
                    normalized_data.get("event_organizer_id")[i] if normalized_data.get("event_organizer_id") and i < len(normalized_data.get("event_organizer_id", [])) else None
                ]
                try:
                    await store_in_normalized_events(event_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized events: {str(e)}")

            elif data_type == "funding":
                funding_data_to_store = [
                    master_id,
                    normalized_data.get("company_name")[i] if normalized_data.get("company_name") and i < len(normalized_data.get("company_name", [])) else None,
                    normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers") and i < len(normalized_data.get("company_decision_makers", [])) else [],
                    normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position") and i < len(normalized_data.get("company_decision_makers_position", [])) else [],
                    normalized_data.get("funding_round")[i] if normalized_data.get("funding_round") and i < len(normalized_data.get("funding_round", [])) else None,
                    normalized_data.get("amount_raised")[i] if normalized_data.get("amount_raised") and i < len(normalized_data.get("amount_raised", [])) else None,
                    normalized_data.get("currency")[i] if normalized_data.get("currency") and i < len(normalized_data.get("currency", [])) else None,
                    normalized_data.get("investor_companies")[i] if normalized_data.get("investor_companies") and i < len(normalized_data.get("investor_companies", [])) else [],
                    normalized_data.get("investor_people")[i] if normalized_data.get("investor_people") and i < len(normalized_data.get("investor_people", [])) else [],
                ]

                try:
                    await store_in_normalized_funding(funding_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized funding: {str(e)}")

            elif data_type == "hiring":
                hiring_data_to_store = [
                    master_id,
                    normalized_data.get("company_name")[i] if normalized_data.get("company_name") and i < len(normalized_data.get("company_name", [])) else None,
                    normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers") and i < len(normalized_data.get("company_decision_makers", [])) else [],
                    normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position") and i < len(normalized_data.get("company_decision_makers_position", [])) else [],
                    normalized_data.get("job_roles")[i] if normalized_data.get("job_roles") and i < len(normalized_data.get("job_roles", [])) else [],
                    normalized_data.get("hiring_reasons")[i] if normalized_data.get("hiring_reasons") and i < len(normalized_data.get("hiring_reasons", [])) else []
                ]
                try:
                    await store_in_normalized_hiring(hiring_data_to_store, pool)
                except Exception as e:
                    logger.error(f"Failed to store normalized hiring data: {str(e)}")

        all_normalized_data.append(normalized_data)
        logger.info(f"Normalized {data_type} data from {name}")

    async with aiofiles.open("normalized.txt", "a") as file:
        await file.write(json.dumps(all_normalized_data, indent=2))

    logger.info("Done normalizing ingested data")

    #2.3 ==========Put In Normalization-Enrichment Queue===========
    logger.info("Adding normalized data to queues...")

    await normalization_to_enrichment_queue.put(all_normalized_data)
    await normalization_to_storage_queue.put(all_normalized_data)

    logger.info(f"Done adding {len(all_normalized_data)} normalized items to queues")

    return {
        "normalization_to_enrichment": normalization_to_enrichment_queue,
        "normalization_to_storage": normalization_to_storage_queue
    }

if __name__ == "__main__":
    async def demo():
        #Populate ingestion_to_normalization_queue
        ingestion_to_normalization_queue = asyncio.Queue()
        normalization_to_enrichment_queue = asyncio.Queue()
        normalization_to_storage_queue = asyncio.Queue()

        mock_fetched_data = [
            #('finsmes', {
                #"type": "funding",
                #"source": ["FinSMEs"],
                #"title": [],
                #"link": ["https://www.finsmes.com/2025/10/socratix-ai-raises-4-1m-in-seed-funding.htm"],
                #"article_date": ["2025-10-29"],
                #"company_name": ["Socratix AI"],
                #"city": [],
                #"country": [],
                #"company_decision_makers": [["Riya Jagetia", "Satya Vasanth Tumati"]],
                #"company_decision_makers_position": [["Co-founder", "Co-founder"]],
                #"funding_round": ["Seed"],
                #"amount_raised": ["$4.1M"],
                #"currency": ["USD"],
                #"investor_companies": [["Pear VC", "Y Combinator", "Twenty Two Ventures", "Transpose Platform Management"]],
                #"investor_people": [[]],
                #"tags": [["AI", "fintech", "fraud", "risk", "startup", "seed funding"]]
            #}),
            #('techcrunch', {
                #"type": "funding",
                #"source": ["TechCrunch"],
                #"title": [],
                #"link": ["https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-app/"],
                #"article_date": ["2025-10-28"],
                #"company_name": ["Mem0"],
                #"city": [],
                #"country": [],
                #"company_decision_makers": [["Taranjeet Singh", "Deshraj Yadav"]],
                #"company_decision_makers_position": [["Founder", "Co-founder and CTO"]],
                #"funding_round": ["Series A"],
                #"amount_raised": ["$24M"],
                #"currency": ["USD"],
                #"investor_companies": [["Basis Set Ventures", "Kindred Ventures", "Y Combinator", "Peak XV Partners", "GitHub Fund"]],
                #"investor_people": [["Dharmesh Shah", "Scott Belsky", "Olivier Pomel", "Thomas Dohmke", "Paul Copplestone", "James Hawkins", "Lukas Biewald", "Brian Balfour", "Philip Rathle", "Jennifer Taylor", "Lan Xuezhao"]],
                #"tags": [["AI", "LLM", "memory", "open source", "API", "developers", "startup", "funding", "infrastructure", "Seed Funding"]]
            #}),
            ('startuphub', {'type': 'funding', 'source': ['Startuphub'], 'title': ['Gamma Raises $68M Series B at $2.1B Valuation, Surpasses $100M ARR', 'Ex-Google Talents Majestic Labs Lands $100M to Redefine AI Big Google News for Infrastructure', 'Scribe Raises $25M to Advance AI Process Capture Tools', 'Spectral Compute Raises $6M to Advance Its AI CUDA Compiler', '1Mind Raises $30 Million to Advance Its Autonomous AI Sales Agent', 'EVE, the first Inbox Revenue Engine for B2B small businesses, raises $2M to end lost revenue hidden in inboxes', 'Wonderful Raises $100M to Advance AI Customer Service Agents', 'Beside funding nets $32M to build an AI for the real economy', 'Euler Raises €2M to Advance AI Software for 3D Printing', 'SuperMe Launch: An AI Network Aims to Fix Professional Advice', 'CERPRO Raises €2M to Advance AI Quality Assurance', 'AirOps Secures $40M for AI Search Content', 'Tenzai Raises $75 Million in Record Seed Round to Build an AI Hacker That Secures Code Written by AI', 'Magic Patterns Raises $6M Series A and Launches Magic Patterns 2.0', 'Neros Lands $75M in Funding to Scale Military Drone Production', 'Delvitech Raises $40M to Advance AI Optical Inspection', 'CoLab raises $72M to advance its AI engineering platform', 'FALKIN raises $2M to advance AI scam protection'], 'link': ['https://www.startuphub.ai/ai-news/funding-round/2025/gamma-raises-68m-series-b-at-2-1b-valuation-surpasses-100m-arr/', 'https://www.startuphub.ai/ai-news/funding-round/2025/ex-google-talents-majestic-labs-lands-100m-to-redefine-ai-big-google-news-for-infrastructure/', 'https://www.startuphub.ai/ai-news/funding-round/2025/scribe-raises-25m-to-advance-ai-process-capture-tools/', 'https://www.startuphub.ai/ai-news/funding-round/2025/spectral-compute-raises-6m-to-advance-its-ai-cuda-compiler/', 'https://www.startuphub.ai/ai-news/funding-round/2025/1mind-raises-30-million-to-advance-its-autonomous-ai-sales-agent/', 'https://www.startuphub.ai/ai-news/funding-round/2025/eve-the-first-inbox-revenue-engine-for-b2b-small-businesses-raises-2m-to-end-lost-revenue-hidden-in-inboxes/', 'https://www.startuphub.ai/ai-news/funding-round/2025/wonderful-raises-100m-to-advance-ai-customer-service-agents/', 'https://www.startuphub.ai/ai-news/funding-round/2025/beside-funding-nets-32m-to-build-an-ai-for-the-real-economy/', 'https://www.startuphub.ai/ai-news/funding-round/2025/euler-raises-e2m-to-advance-ai-software-for-3d-printing/', 'https://www.startuphub.ai/ai-news/funding-round/2025/superme-launch-an-ai-network-aims-to-fix-professional-advice/', 'https://www.startuphub.ai/ai-news/funding-round/2025/cerpro-raises-e2m-to-advance-ai-quality-assurance/', 'https://www.startuphub.ai/ai-news/funding-round/2025/airops-secures-40m-for-ai-search-content/', 'https://www.startuphub.ai/ai-news/funding-round/2025/tenzai-raises-75-million-in-record-seed-round-to-build-an-ai-hacker-that-secures-code-written-by-ai/', 'https://www.startuphub.ai/ai-news/funding-round/2025/magic-patterns-raises-6m-series-a-and-launches-magic-patterns-2-0/', 'https://www.startuphub.ai/ai-news/funding-round/2025/neros-lands-75m-in-funding-to-scale-military-drone-production/', 'https://www.startuphub.ai/ai-news/funding-round/2025/delvitech-raises-40m-to-advance-ai-optical-iaises-72m-to-advance-its-ai-engineering-platform/', 'https://www.startuphub.ai/ai-news/funding-round/2025/falkin-raises-2m-to-advance-ai-scam-protection/'], 'article_date': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-XX-XX', '2025-XX-XX', '2025-XX-XX', '2025-XX-XX', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '', ''], 'company_name': ['Gamma', 'Majestic Labs', 'Scribe', 'Spectral Compute', '1Mind', 'EVE', 'Wonderful', 'Beside', 'Euler', 'SuperMe', 'CERPRO', 'AirOps', 'Tenzai', 'Magic Patterns', 'Neros', 'Delvitech', 'CoLab Software', 'FALKIN'], 'city': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', 'Los Angeles', '', '', ''], 'country': ['', '', '', '', '', '', '', '', 'Iceland', '', '', '', '', '', 'USA', 'Switzerland', '', ''], 'company_decision_makers': [[], ['Ofer Shacham', 'Masumi Reynders', 'Sha Rabii'], [], [], ['Amanda Kahlow'], ['Vadim Rogovskiy'], [], ['Maxime Germain'], [], ['Casey Winters'], [], [], ['Pavel Gurvich', 'Ariel Zeitlin', 'Ofri Ziv', 'Itamar Tal', 'Aner Mazur'], ['Alex Danilowicz'], [], [], [], []], 'company_decision_makers_position': [[], ['Founder', 'Founder', 'Founder'], [], [], ['Founder'], ['CEO', 'Co-founder'], [], ['CEO'], [], ['Co-founder and CEO'], [], [], ['co-founder and CEO', 'co-founder', 'co-founder', 'co-founder', 'co-founder'], ['CEO and co-founder'], [], [], [], []], 'funding_round': ['Series B', 'Series A', 'Series B', 'Seed', '', 'Pre-seed', 'Series A', 'Series A', 'Seed', 'Seed', 'Pre-seed', 'Series B', 'Seed', 'Series A', 'Series B', 'Series B', 'Series C', 'Pre-seed'], 'amount_raised': ['$68M', '$100M', '$25M', '$6M', '$30 million', '$2 million', '$100 million', '$32 million', '€2 million', '$6.8 million', '€2 million', '$40 million', '$75 million', '$6 million', '$75 million', '$40 million', '$72 million', '$2 million'], 'currency': ['USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'EUR', 'USD', 'EUR', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD'], 'investor_companies': [['Andreessen Horowitz'], ['Bow Wave Capital', 'Lux Capital'], ['Redpoint Ventures'], ['Costanoa', 'Crucible'], [], ['Firsthand.VC', 'a16z’s Scout Fund', 'Acquisition.com Ventures', 'Geek Ventures', 'Founders Future', 'Punch Capital', 'Silicon Gardens'], [], ['EQT Ventures', 'Index Ventures'], ['Frumtak Ventures', 'Kvanted'], ['Greylock'], ['seed+speed Ventures', 'D11Z'], ['Greylock'], ['Greylock Partners', 'Battery Ventures', 'Lux Capital', 'Swish Ventures'], ['Standard Capital', 'Y Combinator', 'Essence VC', 'Pioneer Fund', 'Twenty Two Ventures'], ['Sequoia Capital', 'Vy Capital US', 'Interlagos'], ['EGS Beteiligungen', 'CREADD Ventures'], ['Intrepid Growth Partners', 'Insight Partners', 'Y Combinator'], ['TriplePoint Ventures', 'Notion Capital', 'BackFuture Ventures']], 'investor_people': [[], [], [], [], [], ['Simon Chan'], [], ['Martin Mignot'], [], ['Mike Duboe'], [], [], ['Asheem Chandna'], [], [], [], [], []], 'tags': [['AI', 'visual AI', 'storytelling platform', 'business communication', 'presentations'], ['AI infrastructure', 'memory wall', 'server architecture', 'GPU', 'LLMs'], ['AI', 'process capture', 'how-to guides', 'business workflows', 'productivity'], ['AI', 'CUDA compiler', 'GPU', 'hardware compatibility', 'Nvidia'], ['AI', 'sales agent', 'autonomous AI', 'sales technology'], ['Inbox Revenue Engine', 'B2B', 'small businesses', 'AI', 'CRM', 'revenue intelligence', 'email', 'automation', 'pre-seed'], ['AI', 'customer service', 'AI agents', 'Series A'], ['AI', 'intelligent assistant', 'real economy', 'contractors', 'real estate agents', 'plumbers', 'dispatchers', 'mobile UX', 'communication tools', 'smart receptionist', 'chief of staff', 'Series A'], ['AI', '3D printing', 'industrial', 'software', 'manufacturing', 'startup', 'funding'], ['AI', 'professional network', 'startup', 'funding', 'conversational AI', 'LLMs', 'advice', 'expertise'], ['AI', 'quality assurance', 'industrial', 'manufacturing', 'startup', 'funding', 'software', 'automation'], ['AI', 'search', 'content engineering', 'platform', 'funding', 'startup', 'enterprise', 'marketing'], ['AI', 'cybersecurity', 'penetration testing', 'seed funding', 'security', 'agentic AI'], ['AI', 'design tool', 'product development', 'SaaS', 'Series A', 'startup', 'UI/UX', 'automation'], ['defense technology', 'drones', 'military', 'Series B', 'manufacturing', 'unmanned aerial systems', 'USA'], ['AI', 'optical inspection', 'electronics manufacturing', 'quality control', 'Series B', 'Switzerland', 'automation'], ['AI', 'engineering platform', 'manufacturing', 'design', 'software', 'funding', 'Series C'], ['digital safety', 'AI', 'scam protection', 'fintech', 'banking', 'cybersecurity', 'funding', 'Pre-seed']]})
        ]

        for data in mock_fetched_data:
            await ingestion_to_normalization_queue.put(data)
            print("Data added")

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            x = await main(pool, ingestion_to_normalization_queue, normalization_to_enrichment_queue, normalization_to_storage_queue)
            print(x['normalization_to_storage'].qsize())

    asyncio.run(demo())