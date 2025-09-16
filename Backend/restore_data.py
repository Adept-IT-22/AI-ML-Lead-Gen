import json
import httpx
import aiofiles
import asyncio
import logging
import yappi
from flask import Flask, jsonify, request
from flask_cors import CORS
from decimal import Decimal
from typing import List, Dict, Any, Awaitable, Union, Callable

from ingestion_module.funding.finsmes.fetch import main as finsmes_main
from ingestion_module.funding.tech_eu.fetch import main as tech_eu_main
from ingestion_module.funding.techcrunch.fetch import main as techcrunch_main
from ingestion_module.hiring.hacker_news.fetch import main as hacker_news_main
from ingestion_module.events.eventbrite.fetch import main as eventbrite_main
from utils.db_queries import *
from utils.data_normalization import *
from services.db_service import *
from services.email_sending import *
from normalization_module.event_normalization import normalize_event_data
from normalization_module.funding_normalization import normalize_funding_data
from normalization_module.hiring_normalization import normalize_hiring_data
from enrichment_module.organization_search import org_search as apollo_org_search
from enrichment_module.bulk_org_enrichment import bulk_org_enrichment 
from enrichment_module.single_org_enrichment import single_org_enrichment
from enrichment_module.people_search import people_search
from enrichment_module.people_enrichment import people_enrichment
from helpers.helpers import *
#==============2. NORMALIZATION================
#2.1 =========Fetch from queue============
logger.info("Normalizing ingested data....")
all_data = {
    "type": "funding",
    "source": "FinSMEs",
    "title": [],
    "link": [
      "https://www.finsmes.com/2025/08/darwin-ai-closes-4-5m-in-additional-seed-funding.html",
      "https://www.finsmes.com/2025/06/nexchain-secures-strategic-funding-to-lead-the-ai-crypto-market.html",
      "https://www.finsmes.com/2025/07/kuvi-ai-raises-700k-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/prop-ai-raises-1-5m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/07/sciencia-ai-raises-funding-round.html",
      "https://www.finsmes.com/2025/08/method-ai-raises-20m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/07/enquire-ai-closes-3m-convertible-note-round.html",
      "https://www.finsmes.com/2025/07/memories-ai-raises-8m-in-seed-funding.html",
      "https://www.finsmes.com/2025/09/geniez-ai-raises-6m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/pwin-ai-raises-10m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/argon-ai-raises-5-5m-in-seed-funding.html",
      "https://www.finsmes.com/2025/09/teton-ai-raises-20m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/06/databahn-ai-raises-17m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/07/emerald-ai-raises-24-5m-in-funding.html",
      "https://www.finsmes.com/2025/06/bolo-ai-raises-8-1m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/wordsmith-ai-raises-25m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/06/kosmc-ai-raises-200k-in-pre-seed-funding-round.html",
      "https://www.finsmes.com/2025/07/scrunch-ai-raises-15m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/08/resolvd-ai-raises-1-6m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/08/lawpro-ai-closes-seed-funding-round.html",
      "https://www.finsmes.com/2025/09/demand-ai-group-raises-2-5m-in-funding.html",
      "https://www.finsmes.com/2025/09/recall-ai-closes-38m-series-b-funding.html",
      "https://www.finsmes.com/2025/07/trupeer-ai-raises-3m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/veris-ai-raises-8-5m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/synthflow-ai-raises-20m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/07/castellum-ai-raises-8-5m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/09/leo-ai-raises-9-7m-in-seed-funding.html",
      "https://www.finsmes.com/2025/08/menos-ai-raises-5-2m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/warden-ai-raises-funding.html",
      "https://www.finsmes.com/2025/07/opper-ai-raises-3m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/07/motor-ai-raises-20m-in-funding.html",
      "https://www.finsmes.com/2025/07/spacely-ai-raises-us-1m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/iterate-ai-raises-6-4m-in-funding.html",
      "https://www.finsmes.com/2025/08/translucent-ai-raises-7m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/manex-ai-raises-e8m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/caseflood-ai-raises-3-2m-in-funding.html",
      "https://www.finsmes.com/2025/08/loman-ai-raises-3-5m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/reveng-ai-raises-4-15m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/gridfree-ai-raises-5m-in-funding.html",
      "https://www.finsmes.com/2025/09/pascal-ai-raises-3-1m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/thread-ai-raises-20m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/06/pano-ai-raises-44m-in-series-b-funding.html",
      "https://www.finsmes.com/2025/06/klutch-ai-raises-8m-in-seed-funding.html",
      "https://www.finsmes.com/2025/09/penguin-ai-secures-29-7m-in-venture-funding.html",
      "https://www.finsmes.com/2025/08/interhuman-ai-raises-e2m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/06/backops-ai-raises-6m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/moonshine-ai-raises-funding.html",
      "https://www.finsmes.com/2025/08/alignmt-ai-raises-6-5m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/julius-ai-raises-10m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/autonomize-ai-raises-28m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/06/sema4-ai-raises-25m-in-series-a-extension.html",
      "https://www.finsmes.com/2025/06/interactly-ai-raises-pre-seed-funding.html",
      "https://www.finsmes.com/2025/08/tote-ai-raises-22-6m-in-funding.html",
      "https://www.finsmes.com/2025/08/celestial-ai-closes-255m-series-c1.html",
      "https://www.finsmes.com/2025/09/joint-ai-receives-315k-funding-from-the-richard-king-mellon-foundation.html",
      "https://www.finsmes.com/2025/08/refold-ai-raises-6-5m-in-funding.html",
      "https://www.finsmes.com/2025/08/comp-ai-raises-2-6m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/06/voda-ai-raises-series-a-funding.html",
      "https://www.finsmes.com/2025/09/architect-ai-raises-gbp-3-5m-in-funding.html",
      "https://www.finsmes.com/2025/06/horizon3-ai-raises-100m-in-series-d-funding.html",
      "https://www.finsmes.com/2025/07/chai-ai-raises-additional-funding-total-to-over-55m.html",
      "https://www.finsmes.com/2025/08/streamline-ai-raises-8-6m-in-series-a-funding.html",
      "https://www.finsmes.com/2025/07/radical-ai-raises-55m-in-seed-funding.html",
      "https://www.finsmes.com/2025/08/vox-ai-raises-e7-5m-in-seed-funding.html",
      "https://www.finsmes.com/2025/06/voicecare-ai-raises-4-54m-in-funding.html",
      "https://www.finsmes.com/2025/08/bhindi-ai-raises-4m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/07/nexxa-ai-raises-4-4m-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/08/sima-ai-raises-85m-in-funding.html",
      "https://www.finsmes.com/2025/07/litero-ai-raises-800k-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/07/apera-ai-raises-series-a-funding.html",
      "https://www.finsmes.com/2025/09/eloquent-ai-raises-7-4m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/mozart-ai-raises-530k-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/07/inntelo-ai-raises-over-500k-in-pre-seed-funding.html",
      "https://www.finsmes.com/2025/06/ryght-ai-raises-3m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/dropzone-ai-raises-37m-series-b-funding.html",
      "https://www.finsmes.com/2025/08/zipline-ai-raises-7m-in-seed-funding.html",
      "https://www.finsmes.com/2025/07/spear-ai-raises-seed-funding.html",
      "https://www.finsmes.com/2025/07/matrice-ai-expands-seed-funding.html",
      "https://www.finsmes.com/2025/08/ohai-ai-raises-new-funding.html",
      "https://www.finsmes.com/2025/07/callidus-legal-ai-raises-10m-in-funding.html",
      "https://www.finsmes.com/2025/07/genesis-ai-raises-105m-in-funding.html"
    ],
    "article_date": [
      "2025-10-27",
      "",
      "2025-07-30",
      "2025-06-17",
      "2025-07-01",
      "2025-08-21",
      "2025-06-01",
      "2025-07-24",
      "2025-09-05",
      "2025-06-03",
      "2025-07-02",
      "2025-09-09",
      "2025-06-26",
      "2025-07-01",
      "2025-06-11",
      "2025-06-04",
      "2025-06-06",
      "2025-07-23",
      "2025-08-06",
      "2025-08-14",
      "2025-09-15",
      "2025-09-04",
      "2025-07-15",
      "2025-06-03",
      "2025-06-25",
      "2025-07-08",
      "2025-09-02",
      "2025-08-07",
      "2025-07-16",
      "2025-07-14",
      "2025-07-14",
      "2025-07-22"
    ],
    "company_name": [
      "darwin ai",
      "nexchain",
      "kuvi.ai",
      "prop-ai",
      "sciencia ai",
      "method ai",
      "enquire.ai",
      "memories.ai",
      "geniez ai",
      "pwin.ai",
      "argon ai",
      "teton.ai",
      "databahn.ai",
      "emerald ai",
      "bolo ai",
      "wordsmith ai",
      "kosmc ai",
      "scrunch ai",
      "resolvd ai",
      "lawpro.ai",
      "demand ai group",
      "recall.ai",
      "trupeer.ai",
      "veris ai",
      "synthflow ai",
      "castellum.ai",
      "leo ai",
      "menos ai",
      "warden ai",
      "opper ai",
      "motor ai",
      "spacely ai"
    ],
    "city": [],
    "country": [],
    "company_decision_makers": [
      [
        "Lautaro Schiaffino",
        "Ezequiel Sculli"
      ],
      [
        "Logan Reynolds"
      ],
      [
        "Dylan Dewdney",
        "Jay Nasr",
        "Maxim Sindall"
      ],
      [
        "Ranime El-Skaff"
      ],
      [],
      [
        "Doug Teany"
      ],
      [
        "Cenk Sidar"
      ],
      [
        "Dr. Shawn Shen",
        "Ben Zhou"
      ],
      [
        "Gil Peleg"
      ],
      [
        "Vishwas Lele"
      ],
      [
        "Samy Danesh"
      ],
      [
        "Mikkel Wad Thorsen"
      ],
      [
        "Nanda Santhana"
      ],
      [
        "Dr. Varun Sivaram"
      ],
      [
        "Diti Sood",
        "Dr. Lalit Jain"
      ],
      [
        "Ross Mcnairn"
      ],
      [
        "Ankur Gupta",
        "Manavta Narula"
      ],
      [
        "Chris Andrew"
      ],
      [],
      [
        "Jeremy Schmerling"
      ],
      [
        "Michael Whife",
        "Charlie Whife"
      ],
      [],
      [
        "Shivali Goyal",
        "Pritish Gupta"
      ],
      [
        "Mehdi Jamei"
      ],
      [
        "Hakob Astabatsyans",
        "Albert Astabatsyans",
        "Sassun Mirzakhan-Saky"
      ],
      [
        "Peter Piatetsky"
      ],
      [
        "Dr. Maor Farid",
        "Moti Moravia"
      ],
      [
        "William Wu",
        "Xiang Pan"
      ],
      [
        "Jeffrey Pole",
        "Eduard Schikurski"
      ],
      [
        "G\u00f6ran Sandahl"
      ],
      [
        "Roy Uhlmann",
        "Adam Bahlke"
      ],
      [
        "Paruey Anadirekkul"
      ]
    ],
    "company_decision_makers_position": [
      [
        "Founder",
        "Founder"
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
      [],
      [
        "Ceo"
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
        "Ceo"
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
        "Co-Founder And Ceo"
      ],
      [
        "Ceo And Founder"
      ],
      [
        "Co-Founder",
        "Co-Founder"
      ],
      [
        "Ceo"
      ],
      [
        "Founder",
        "Founder"
      ],
      [
        "Ceo"
      ],
      [],
      [
        "Ceo"
      ],
      [],
      [],
      [],
      [
        "Ceo"
      ],
      [
        "Founder",
        "Founder",
        "Founder"
      ],
      [
        "Co-Founder And Ceo"
      ],
      [
        "Founder",
        "Founder"
      ],
      [
        "Ceo",
        "Cto"
      ],
      [
        "Ceo",
        "Cto"
      ],
      [
        "Ceo"
      ],
      [],
      [
        "Ceo"
      ]
    ],
    "funding_round": [
      "Seed",
      "Strategic Investment Round",
      "Seed",
      "Pre-Seed",
      "Funding Round",
      "Series A",
      "Convertible Note",
      "Seed",
      "Seed",
      "Seed",
      "Seed",
      "Series A",
      "Series A",
      "Seed",
      "Seed",
      "Series A",
      "Pre-Seed Funding",
      "Series A Funding",
      "Pre-Seed Funding",
      "Seed Funding",
      "",
      "Series B",
      "Seed",
      "Seed",
      "Series A",
      "Series A",
      "Seed",
      "Seed",
      "Funding",
      "Pre-Seed",
      "Funding",
      "Seed"
    ],
    "amount_raised": [
      "4500000",
      "",
      "700000",
      "1500000",
      "",
      "20000000",
      "3000000",
      "8000000",
      "6000000",
      "120000000",
      "5500000",
      "20000000",
      "17000000",
      "24500000",
      "8100000",
      "25000000",
      "200000",
      "15000000",
      "1600000",
      "",
      "2500000",
      "38000000",
      "3000000",
      "8500000",
      "20000000",
      "8500000",
      "9700000",
      "5200000",
      "",
      "3000000",
      "20000000",
      "1000000"
    ],
    "currency": [
      "US Dollar",
      "",
      "US Dollar",
      "US Dollar",
      "",
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
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "US Dollar",
      "",
      "US Dollar",
      "US Dollar",
      "US Dollar"
    ],
    "investor_companies": [
      [
        "Base10 Partners"
      ],
      [
        "Shima Capital",
        "Animoca Brands",
        "Outlier Ventures",
        "Dream Ventures"
      ],
      [
        "Moon Pursuit Capital"
      ],
      [
        "Plus Vc",
        "Joa Capital",
        "Select Ventures",
        "Oraseya Capital",
        "Plug And Play"
      ],
      [],
      [
        "Private Family Office",
        "Cleveland Clinic",
        "Jobsohio Growth Capital Fund"
      ],
      [],
      [
        "Susa Ventures",
        "Samsung Next",
        "Crane Venture Partners",
        "Fusion Fund",
        "Seedcamp",
        "Creator Ventures"
      ],
      [
        "Stageone Ventures",
        "Canapi Ventures"
      ],
      [],
      [
        "Crosslink Capital",
        "Wireframe Ventures",
        "Y Combinator",
        "Pioneer Fund"
      ],
      [
        "Plural",
        "Bertelsmann Investments",
        "Antler Elevate",
        "Nebular",
        "Psv Tech"
      ],
      [
        "Forgepoint Capital",
        "S3 Ventures",
        "Gtm Capital"
      ],
      [
        "Radical Ventures",
        "Nventures",
        "Amplo",
        "Crv",
        "Neotribe"
      ],
      [
        "True Ventures",
        "Benchstrength",
        "Accomplice",
        "J Ventures",
        "Beat Ventures"
      ],
      [
        "Index Ventures"
      ],
      [],
      [
        "Decibel",
        "Mayfield",
        "Homebrew"
      ],
      [
        "Spice Capital",
        "Betaworks",
        "Factorial Capital"
      ],
      [
        "Scopus Ventures"
      ],
      [],
      [
        "Bessemer Venture Partners",
        "Hubspot Ventures",
        "Salesforce Ventures",
        "Ridge Ventures",
        "Y Combinator",
        "Rtp Ventures"
      ],
      [
        "Rtp Global",
        "Salesforce Ventures"
      ],
      [
        "Decibel Ventures",
        "Acrew Capital",
        "The House Fund"
      ],
      [
        "Accel",
        "Atlantic Labs",
        "Singular"
      ],
      [
        "Curql",
        "Btech Consortium",
        "Framework Venture Partners",
        "Spider Capital",
        "Remarkable Ventures",
        "Cameron Ventures"
      ],
      [
        "Flint Capital",
        "A16Z Scout",
        "Techaviv",
        "Two Lanterns Vc"
      ],
      [],
      [
        "Playfair"
      ],
      [
        "Luminar Ventures",
        "Emblem Venture Capital",
        "Greens Capital"
      ],
      [
        "Segenia Capital",
        "Ecapital"
      ],
      [
        "Proptech Farm Fund Iii",
        "Utc Holdings Co., Ltd."
      ]
    ],
    "investor_people": [
      [],
      [],
      [],
      [],
      [],
      [],
      [],
      [],
      [],
      [
        "Sanju Bansal"
      ],
      [],
      [],
      [
        "Ernie Bio"
      ],
      [],
      [],
      [],
      [],
      [],
      [
        "Olivier Pomel",
        "Clement Delaunge",
        "Ben Tossell"
      ],
      [],
      [],
      [
        "Paul Graham",
        "Solomon Hykes",
        "Michael Siebel",
        "Eoghan Mccabe"
      ],
      [],
      [
        "Ian Livingstone",
        "Idris Mokhtarzada",
        "Dorothy Chang"
      ],
      [],
      [],
      [
        "Bertrand Sicot",
        "Prof. Yossi Matias"
      ],
      [],
      [],
      [],
      [],
      [
        "Wannaporn Phornprapha",
        "Ted Poshakrishna Thirapatana",
        "Mek Srunyu Stittri"
      ]
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
      [],
      []
    ]
  }
async def main():
    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
        all_normalized_data = []
        #Check if links are in normalized master return those that aren't
        unstored_links = []
        links = all_data.get("link")
        for link in links:
            data_is_in_db = await is_data_in_db(pool, link)
            if data_is_in_db:
                continue
            else:
                unstored_links.append(link)

        print(len(unstored_links))

        for i, link in enumerate(unstored_links):
            data = {
                "type": all_data.get("type"),
                "source": all_data.get("source"),
                "link": link,
                "title": all_data.get("title")[i] if i < len(all_data.get("title", [])) else [""],
                "article_date": all_data.get("article_date")[i] if i < len(all_data.get("article_date", [])) else [""],
                "company_name": all_data.get("company_name")[i] if i < len(all_data.get("company_name", [])) else [""],
                "city": all_data.get("city")[i] if i < len(all_data.get("city", [])) else [""],
                "country": all_data.get("country")[i] if i < len(all_data.get("country", [])) else [""],
                "company_decision_makers": [all_data.get("company_decision_makers")[i]] if i < len(all_data.get("company_decision_makers", [])) else [[]],
                "company_decision_makers_position": [all_data.get("company_decision_makers_position")[i]] if i < len(all_data.get("company_decision_makers_position", [])) else [[]],
                "funding_round": [all_data.get("funding_round")[i]] if i < len(all_data.get("funding_round", [])) else [""],
                "amount_raised": [all_data.get("amount_raised")[i]] if i < len(all_data.get("amount_raised", [])) else [""],
                "currency": all_data.get("currency")[i] if i < len(all_data.get("currency", [])) else [""],
                "investor_companies": [all_data.get("investor_companies")[i]] if i < len(all_data.get("investor_companies", [])) else [[]],
                "investor_people": [all_data.get("investor_people")[i]] if i < len(all_data.get("investor_people", [])) else [[]],
                "tags": [all_data.get("tags")[i]] if i < len(all_data.get("tags", [])) else [[]]
            }


            # 2.2 ========== Normalize data ===============
            data_type = data.get("type")

            normalized_data = data
            x = normalized_data.get("company_name")
            if not x or x == [""]:
                continue
            else:
                # Step 2: Insert master (one row per dataset)
                normalized_master_data_to_store = [
                    normalized_data.get("type", ""),
                    normalized_data.get("source", ""),
                    link,
                    normalized_data.get("title") if normalized_data.get("title") else None,
                    normalized_data.get("city") if normalized_data.get("city") else None,
                    normalized_data.get("country") if normalized_data.get("country") else None,
                    normalized_data.get("tags") if normalized_data.get("tags")else []
                ]
                #data_is_in_db = await is_data_in_db(pool, link)
                #if data_is_in_db:
                    #continue
                #master_id = await store_in_normalized_master(normalized_master_data_to_store, pool)

                # Step 3: Insert children
                if data_type == "event":
                    event_data_to_store = [
                        #master_id,
                        normalized_data.get("event_id")[i] if normalized_data.get("event_id")[i] else None,
                        normalized_data.get("event_summary")[i] if normalized_data.get("event_summary")[i] else None,
                        normalized_data.get("event_is_online")[i] if normalized_data.get("event_is_online")[i] else None,
                        normalized_data.get("event_organizer_id")[i] if normalized_data.get("event_organizer_id")[i] else None
                    ]
                    try:
                        await store_in_normalized_events(event_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized events: {str(e)}")

                elif data_type == "funding":
                    funding_data_to_store = [
                        #master_id,
                        normalized_data.get("company_name") if normalized_data.get("company_name") else None,
                        normalized_data.get("company_decision_makers") if normalized_data.get("company_decision_makers") else [],
                        normalized_data.get("company_decision_makers_position")if normalized_data.get("company_decision_makers_position") else [] ,
                        normalized_data.get("funding_round") if normalized_data.get("funding_round") else None,
                        normalized_data.get("amount_raised") if normalized_data.get("amount_raised")else None,
                        normalized_data.get("currency") if normalized_data.get("currency") else None,
                        normalized_data.get("investor_companies") if normalized_data.get("investor_companies") else [],
                        normalized_data.get("investor_people")if normalized_data.get("investor_people") else [],
                    ]

                    #try:
                        #await store_in_normalized_funding(funding_data_to_store, pool)
                    #except Exception as e:
                        #logger.error(f"Failed to store normalized funding data: {str(e)}")

                elif data_type == "hiring":
                    hiring_data_to_store = [
                        #master_id,
                        normalized_data.get("company_name")[i] if normalized_data.get("company_name")[i] else None,
                        normalized_data.get("company_decision_makers")[i] if normalized_data.get("company_decision_makers")[i] else [],
                        normalized_data.get("company_decision_makers_position")[i] if normalized_data.get("company_decision_makers_position")[i] else [],
                        normalized_data.get("job_roles")[i] if normalized_data.get("job_roles")[i] else [],
                        normalized_data.get("hiring_reasons")[i] if normalized_data.get("hiring_reasons")[i] else []
                    ]
                    try:
                        await store_in_normalized_hiring(hiring_data_to_store, pool)
                    except Exception as e:
                        logger.error(f"Failed to store normalized hiring data: {str(e)}")

                all_normalized_data.append(normalized_data)

        async with aiofiles.open("new_normalized.txt", "a") as file:
            await file.write(json.dumps(all_normalized_data, indent=2))

        logger.info("Done normalizing ingested data")

        #2.2 =======Organization Search to Get Org Website=========
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            set_of_orgs_to_search = set()
            searched_orgs = []

            for normalized_company in all_normalized_data:
                each_company = normalized_company.get("company_name", [])

# ==========Check if company exists in DB before enriching=========
                lowercase_company = each_company.lower()
                company_is_in_db = await is_company_in_db(company_name=lowercase_company)
                if not company_is_in_db:
                    set_of_orgs_to_search.add(each_company)

            logger.info("Organizational search started...")

            orgs_to_search = list(set_of_orgs_to_search)
            logger.info(f"Orgs to search\n{orgs_to_search}")
            searched_tasks = [apollo_org_search(client=client, company_name=name) for name in orgs_to_search]
            search_results = await asyncio.gather(*searched_tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed {result}")
                else:
                    searched_orgs.append(result)

            logger.info(f"Completed organization seach for {len(searched_orgs)} companies")

            async with aiofiles.open(f"new_org_search.txt", "a") as org_search_file:
                await org_search_file.write(json.dumps(searched_orgs, indent=2))

            logger.info("Completed organizational search")

    #2.3 ========Bulk Org Enrichment===========
            logger.info("Bulk Org Enrichment started...")
            bulk_enriched_orgs = []

            #Batch orgs in groups of 10
            searched_orgs_length = len(searched_orgs)
            for i in range(0, searched_orgs_length, 10):
                batch = searched_orgs[i: i+10]

                #Extract websites from batch
                bulk_org_websites = []
                for bulk_org_data in batch:
                    if 'organizations' in bulk_org_data and bulk_org_data['organizations']:
                        logger.info(f"Enriching {bulk_org_data.get('organizations')[0].get('name')}")
                        website = bulk_org_data.get('organizations')[0].get('website_url')
                        if website:
                            bulk_org_websites.append(website)
                
                #Perform enrichment on the batch
                if bulk_org_websites:
                    try:
                        bulk_enriched_batch= await bulk_org_enrichment(client=client, company_websites=bulk_org_websites)
                        bulk_enriched_orgs.append(bulk_enriched_batch)
                    except Exception as e:
                        logger.error(f"Failed bulk enrichment for bulk starting at index {i}: {str(e)}")
            
            async with aiofiles.open("new_bulk_org_enrichment.txt", "w") as bulk_org_enrichment_file:
                await bulk_org_enrichment_file.write(json.dumps(bulk_enriched_orgs, indent=2))

            logger.info("Completed Bulk Org Enrichment")

    #2.4 ========Single Org Enrichment===========
            logger.info("Single Org Enrichment started...")

            try:
                single_enriched_orgs = []
                if not bulk_enriched_orgs:
                    logger.error("No bulk enriched orgs")
                    return jsonify({"Error": "No bulk enriched orgs"})
                for single_org in bulk_enriched_orgs[0].get("organizations"):
                    org_domain = single_org.get("primary_domain")
                    single_enriched_org = await single_org_enrichment(client=client, company_website=org_domain)
                    single_enriched_orgs.append(single_enriched_org)
            except Exception as e:
                logger.error(f"Single enrichment failed: {str(e)}")
                
            async with aiofiles.open("new_single_org_enrichment.txt", "w") as single_org_enrichment_file:
                await single_org_enrichment_file.write(json.dumps(single_enriched_orgs, indent=2))

            logger.info("Completed Single Org Enrichment")

    #2.5 ========People Search========
            logger.info("People Search started...")

            #Get org ids
            org_ids = []
            org_domains = []
            for orgs in bulk_enriched_orgs:
                org_data = orgs.get("organizations") #returns a list of dicts
                for each_org in org_data:
                    org_id = each_org.get("id")
                    org_ids.append(org_id)
                    org_domain = each_org.get("primary_domain")
                    org_domains.append(org_domain)
            
            searched_people = await people_search(client=client, org_ids=org_ids, org_domains=org_domains)

            async with aiofiles.open("new_people_search.txt", "w") as people_search_file:
                await people_search_file.write(json.dumps(searched_people, indent=2))

            logger.info("Completed people Search")

    #2.6 ============People Enrichment=============
            logger.info("People Enrichment started....")

            enriched_people = []

            #Get user id's and names
            people_to_enrich = searched_people.get("people", [])
            for person in people_to_enrich:
                user_id = person.get("id", "")
                user_name = person.get("name", "")

                #Call people enrichment API
                enriched_person = await people_enrichment(client=client, user_id=user_id, user_name=user_name)
                enriched_people.append(enriched_person)

            async with aiofiles.open("new_people_enrichment.txt", "w") as people_enrichment_file:
                await people_enrichment_file.write(json.dumps(searched_people, indent=2))

            logger.info("Completed people enrichment")

    #==============4. STORAGE================
    logger.info("Storing data....")

    #Check LIVE DEV DOC for the "necessary data" mentioned below

    #=============Company Data Storage=============
    company_data_to_store = []

    searched_organizations = [orgs[0] for dictionary in searched_orgs if (orgs := dictionary.get("organizations"))]
    bulk_enriched_organizations = bulk_enriched_orgs[0].get("organizations", [])
    single_enriched_organizations = [item.get("organization", []) for item in single_enriched_orgs]

    #Iterate over orgs. Zip will stop when shortest list ends preventing errors
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
                latest_funding_round = funding_events_list[0].get("type") if funding_events_list else None
                unclean_latest_funding_amount = funding_events_list[0].get("amount") if funding_events_list else None
                latest_funding_amount = normalize_amount_raised(unclean_latest_funding_amount) if unclean_latest_funding_amount else None
                latest_funding_currency = funding_events_list[0].get("currency") if funding_events_list else None

                #Get data source (funding, events, hiring) from normalized data
                company_data_source = None
                for normalized_company_info in all_normalized_data:
                    normalized_names = normalized_company_info.get("company_name", [])
                    for normalized_name in normalized_names:
                        if normalized_name.lower() in company_name.lower() or company_name.lower() in normalized_name.lower():
                            company_data_source = normalized_company_info.get("type")
                            break

                company_row = (
                    apollo_id, company_name, website_url, linkedin_url, phone, safe_int(founded_year),
                    safe_decimal(market_cap), safe_decimal(annual_revenue_printed), industries, safe_int(estimated_num_employees), 
                    keywords, safe_decimal(headcount_six_month_growth), safe_decimal(headcount_twelve_month_growth), city,
                    state, country, short_description, safe_decimal(total_funding), technology_names,
                    None, #icp score placeholder
                    None, #notes
                    company_data_source, latest_funding_round, latest_funding_amount, latest_funding_currency
                )

                company_data_to_store.append(company_row)

            except Exception as e:
                logger.error(f"Failed to process company data for storage: {str(e)}")
                continue #Skip this entry and move to the next

    #Store company data in "companies" database
    if company_data_to_store:
            await store_to_db(data_to_store=company_data_to_store, query=company_query, company_or_people="company")
    else:
        logger.warning("No companies to store ❌")

    #==============People Data Storage=================
    people_data_to_store = []

    people_search_data = searched_people.get("people", [])
    people_enrichment_data = enriched_people

    if people_search_data and people_enrichment_data:
        for person_search_data, person_enrichment_data in zip(people_search_data, people_enrichment_data):
            try:
                #From people search API
                apollo_user_id = person_search_data.get("id", "")
                user_first_name = person_search_data.get("first_name", "")
                user_last_name = person_search_data.get("last_name", "")
                user_full_name = person_search_data.get("name", "")
                user_linkedin_url = person_search_data.get("linkedin_url")
                user_title = person_search_data.get("title", "")
                user_email_status = person_search_data.get("email_status", "")
                user_headline = person_search_data.get("headline", "")
                user_organization_id = person_search_data.get("organization_id", "")
                user_seniority = person_search_data.get("seniority", "")
                user_departments = person_search_data.get("departments", [])
                user_subdepartments = person_search_data.get("subdepartments", [])
                user_functions = person_search_data.get("functions", [])

                #From people enrichment API
                user_email = person_enrichment_data.get("person", {}).get("email", "")
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
    asyncio.run(main())