from utils.data_normalization import *
from utils.data_structures.news_data_structure import *
from typing import Dict, List, Any
import logging
import asyncio
import copy
import json

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


"""
ingested_data below looks like this:
    {"finsmes": {
        "type": "funding",
        "source": ["finsmes"],
        "article_link": ["...", "..."],
        etc.
        }
    }
"""

async def normalize_funding_data(ingested_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    if not ingested_data:
        logger.error("No funding data to normalize. Ingested data is empty")
        return {}
    
    #Make a deep copy of the events_data_structure
    logger.info("Normalizing funding data")
    normalized_funding_data = copy.deepcopy(fetched_funding_data)

    normalized_funding_data.update({
        "type": "funding",
        "source": ingested_data.get("source", []),
        "title": [title.strip() for title in ingested_data.get("title", [])],
        "link": [normalize_url(url) for url in ingested_data.get("link", [])],
        "article_date": [str(normalize_date(date)) for date in ingested_data.get("article_date", [])],
        "company_name": [name.strip().lower() for name in ingested_data.get("company_name", [])],
        "city": [normalize_city(city) for city in ingested_data.get("city", [])],
        "country": [normalize_country(country) for country in ingested_data.get("country", [])],
        "company_decision_makers": [normalize_company_decision_makers(decision_maker_list) for decision_maker_list in ingested_data.get("company_decision_makers", [])],
        "company_decision_makers_position": [normalize_company_decision_makers(decision_maker_position_list) for decision_maker_position_list in ingested_data.get("company_decision_makers_position", [])],
        "funding_round": [fround.strip().title() for fround in ingested_data.get("funding_round", [])],
        "amount_raised": [normalize_amount_raised(amount_raised) for amount_raised in ingested_data.get("amount_raised", [])],
        "currency": [normalize_currency(currency) for currency in ingested_data.get("currency", [])],
        "investor_companies": [normalize_company_decision_makers(investor_company_list) for investor_company_list in ingested_data.get("investor_companies", [])],
        "investor_people": [normalize_company_decision_makers(investor_people_list) for investor_people_list in ingested_data.get("investor_people", [])],
        "tags": [normalize_tags(tag) for tag in ingested_data.get("tags", [])]
    })

    logger.info("Done normalizing funding data")
    return normalized_funding_data

if __name__ == "__main__":
    async def main():
        data = {'type': 'funding', 
                'source': ['Reuters', 'Bloomberg.com', 'City AM', 'The AI Journal', 'ZAWYA', 'YourStory.com', 'The SaaS News', 'Elets BFSI', 'FinSMEs', 'FinSMEs', 'AIM Media House', 'BusinessCloud', 'Tech Funding News', 'WWD', 'AI Insider', 'FF News | Fintech Finance', 'Reuters', 'Wamda', 'Indian Startup News', 'Business Wire'], 
                'title': ['Nvidia', 'Vercel Notches $9.3 Billion Valuation in Latest AI Funding Round ', 'AI, robot: Tech firm Dexory lands $165m funding round ', 'KOR Closes Series B Funding to Accelerate Global Growth ', 'Oqood secures $1mln funding to expand AI', 'Gen AI', 'Resistant AI Raises $25 Million Series B ', 'GoodScore secures $13 million in funding to advance AI', 'Resistant AI Raises $25M in Series B Funding ', 'Prezent AI Raises Additional $30M in Funding; Acquires Prezentium ', 'DVC Closes $75 Million Fund to Invest in Series A and B Rounds with AI Model ', 'Patchworks raises £5m to set out AI strategy & expand in US ', 'TravelPerk challenger Navan lands $300M to expand its AI', 'BNTO Launches AI Styling Agent and Secures $15 Million in Series A Funding ', 'Climaty AI Raises $2M to Pioneer Carbon', 'Resistant AI Raises $25 Million in Series B Funding to Empower AI Agents to Fight Fraud and Fincrime ', 'AI startup Modular raises $250 million, seeks to challenge Nvidia dominance ', 'Lucidya secures $30 million in Series B, setting a MENA AI funding record ', 'AI', 'Resistant AI Raises $25 Million in Series B Funding to Empower AI Agents to Fight Fraud and Fincrime '], 
                'link': ['https://news.google.com/rss/articles/CBMiwgFBVV95cUxPUnZpeW1BT2k1SlJDSzJHMmFfT1hCc3RvMEdRcFFaYnR4VUNkUEFCbTRYT1lXOWJBckp3ZnVnQXZZc2JjTFkzMWpiOExuOTYzOWZ3Y0FET0s0bEVRVUtza1g2ZjhkMUVvMkJUdkNXZkZUMFdvaWI4SUVpZWlGTzQ2VS0zdzJiRDBvQzZ0Zm8tTTV0QWFlVFZIOWRiYXFWaGpMbXI4cGRfVmk0WDgzeTlkcWxmV1lTOFNFSWZYSUkwSDg4Zw?oc=5', 'https://news.google.com/rss/articles/CBMitAFBVV95cUxPZkdlOUljdEdUOV9ibkNheVhoNWFRRjRFdG5vWmFCMjFBU1BMd2ZFQ3h2UXpNUXJybVNwREZ3QmY0Z0tLa3RQaDNiV19IdF90UTRJd1VXTUFPTEtpbjZiUkkxaDVSUDFBNjR2dkI4eVFwYXp2bFhkZ2JyTlFRY0ZPSnVXSEgzVzkzcEFaUTl3dkN5R3o1bUV2MkNoRzBXVUdvYWtWbHZBWWZUVnJMSkdneUI5akY?oc=5', 'https://news.google.com/rss/articles/CBMif0FVX3lxTFBjcm12NGRNLTZYX2JkVEFWWjVScFI0UExnT1hqTWpGWjZiWEMzQ1hMNjIwTVE0VElCeHBoSC1vNlJqQWxTNERSZ1RvOXViZjFjLWd4bXM0S29BZDAxems5QWszRTNzdzItTmlQV1gyVjBQUVpSUV9tcmY3Yy0wOXM?oc=5', 'https://news.google.com/rss/articles/CBMiggFBVV95cUxNblhSQjUxQk50TjRDdGVLaXEyakNQVWdFbUdtZkd0QWh6MnBmQ3R0WTBhQUxLNlp5YUN6WkowODJVOERNZUJmZGR1TG10OHVnY3duVWlCWVkzLWdpME5EYVJJRHdMWGxKWENPMENPYy1zeTRWTVBORjhzZlp1anFCRlZ3?oc=5', 'https://news.google.com/rss/articles/CBMiwgFBVV95cUxORVFOZEUtaVFOQjIxX2VZOGk2ZndLZWwyTEcxQlhDUHlZUlo1QWltRm9kN253TC1nNlMwUEc4MDVjbzFOWUc0eHV2NlBKVEdLVVZZZ0dnUlZpdE1Nc0lsX1ZyeVE5SG5PRDhROXo5bl9PanB6bF92ZzgxODRSalJneFd2WjdpRWU3YkNjY1c3YnRseFRrOTBPQmp5R0JRYzlPT25qS3BuY25WeUxTejd3X2JWYUJJbFpsYVNuaGV1SEJBUQ?oc=5', 'https://news.google.com/rss/articles/CBMikwFBVV95cUxNS3FMMHRwZ2dsTDlTbHJLZnk1WGNuWU9TUVNFdDRyb2x3ZmJvMFdGXzRoZ0VyOUZRS0pXR1FpYzdNS1d2LWhpNlQwamJ5bEcwTzZJeWZVZmlkaUNVYnF0dGZUbHh4STZkYzFiOGZTTzN6ZjZKZW82RTZIcjBNV0tWSk44M3lSWHgwZTVaQnVUMFo3LTg?oc=5', 'https://news.google.com/rss/articles/CBMifEFVX3lxTFB0YndCbW5VaVh4QXg0UkZjcmhuR25UanNjUGFxYlkydVVqZTVacG1GZlFvd2lBNnJzdXBEQmRjMjRpQTZQQzI5VVJNSWFJaDNOMFAzUHNjRnNCZl9DOVE4d2JiR3NtZVE3Ykw2WUtEblNIQlRpMkhVSkhjSE0?oc=5', 'https://news.google.com/rss/articles/CBMiqgFBVV95cUxQck1lZVdieHBWXzY5SnNnalQ4TUF4QkpsamJPNlVhSkRmbXZhV0l5REp0SUlYdWdpS2RiMnBQdXRZdHNPUV9NNENHYmpTclh0cVJJZ1RXMlpNRF9EbnRweEs4SzBNdFlBME43eElTT1BYZWdZRHcxUWd6Ykg5eVV5QjNNZlNDQ3VJYVBDZFdKOXVybFpHOG9xWHgza2R0MHZPdDJYSE92WFRjUQ?oc=5', 'https://news.google.com/rss/articles/CBMihwFBVV95cUxNamotV0pnbXRCM05hTHlHTUZBbHJwQ0tjMkZmSDRmZ0x0SjN5TW1EQXQ2UXRNbTBZZzRoOHJIeU1HS3AtY3NtTlY2RURLclZ4R3ZEZUxXU3FmTDFSV0J4Q1JuWVFGenBUeTB6c0xwQllhb1BQbGJKNnRoQzYxRkg0dDVUdm1XT2M?oc=5', 'https://news.google.com/rss/articles/CBMihwFBVV95cUxNRW5uN2RCUVd5NE5sN1Azd1dwQUVzbW94TS1nLXdXSEx1RGc0RFE5Q1A3aERucS10eEpiQTlHRlN1eE1yTU5Ob3VfalU0TUhaODRMQ2k2ZmNMZFdNeVRiNXpWRl83cjZFOXVsOUFPRkZBbFJ1Z2pLM0ZEUDhxTEI5dTFla05Pb3c?oc=5', 'https://news.google.com/rss/articles/CBMiswFBVV95cUxNWlFabGdLQXRlUEJXMGJnOFJhWTNnYVZJWEllRXc4TXdheVNkWWFKc1lnVTRmUWZuMTdjVU5WNVRTWGZlSDJDakxMVGk1T3RPdWo1VEpZTnY4elEtdUJsV3dmcjRqcnc3ZUN4NnV0X0FhZmVRaTJWNUxnQnVSME5UQnhaNDBmT3J3STFpT2RfS2NUQUVKWXpoSHdHYl9iMV84UGZWOWJsSGJTYUpLN0VnWUJUVQ?oc=5', 'https://news.google.com/rss/articles/CBMilAFBVV95cUxPbk9VbU5ZamJLZTVmZHR4VFFiWHFsbjc0NHZyYUMzSWxrLUFxWDZQcU5ENDM1LXpvNzM1QTZlaGhUZlJVU2dia2d4WUlvQTVoUkk1c0JnY3lUdnRhTzVDVG0xaXl4bTJrWWx0aEhTVTNIcUphRi02a0p4YnBHcG8yX2lxN0tIU3lqZkdlZ1loZmFkaElC?oc=5', 'https://news.google.com/rss/articles/CBMigAFBVV95cUxOb0ZuT0NOaXFTcEwtcE9QLWZvMDFVYWZIbzJDcjJNczhlUm0tcW5SU3NEb2pNdVNZQlJ3LVNrRmpKc2RDWVhiSkhQVi1zZDNqUGZyNi0yM2pFTFlDU2lYUDB4eHZCcXFoRjZJZWhJdkQwQi14SWpXTEpQSGUyOXVjMQ?oc=5', 'https://news.google.com/rss/articles/CBMisAFBVV95cUxNMlN1TnAyRmVHdTFpUW1wa05rRHR3eHJaWFF4QkZkRG8xc1ZYX2ttSmI0R0U4a0p1bm1PX2ZSSzlwQXZJQm1oZkFsZ1ZxUUZrRC0xd0tMQXhnNnFrN2JWREtrbFlYblRpQVFYNzdoQ0NBRnNrVzZfZzZ2ajlZOElCbG9CcWZ3anVKNzg4MVVDRlg5VzlmV28wR05lSDByRXV1bDBiSUlMUXBBOVRvc2pSVw?oc=5', 'https://news.google.com/rss/articles/CBMisgFBVV95cUxNczR0UFc1TUJ2Q0NqTmJQV0cyNV8zd1doVHZpbFBXQUJtMElaSE9mb0ZmeFl1Mmg0RjBRYmhNZjl1cktpellYTjAtczg1bGF1XzM3NGdCb3hZaVdnbmVrVnBZRTE1MlBWM29vNDlkaDZoWFJmNDllYjNKdERxaTFISmd4NlpLYzc4c084dERMWEx2d3hlRkxwZXp3a3Y4WGtVRlVqQmNkYVI1cVVJTXhJaXJR?oc=5', 'https://news.google.com/rss/articles/CBMi1gFBVV95cUxNbFJGMEoxd0JiMVk1U0FTblVMOTMxclJYRlRBaE1hUW5saGR2Um9lRWdTVWpHbWtwQXJQVEFUUXNBRElBanoyMFcxV0NOQXRTNVR1WlpNd29QYWhjQ2RRTzhrWWhTUnZleTlyblhoWjA4aVZVWHpnYklnYmZPRTRwclIzZEl4b2pvazBhbkwwTmpwc1RkZy0xUG1pZUxBR3l0MXBnd25NTkVCcmo1NU8zX1g4YUNFMHZCMWVzTERhbFc5bVhWQ1pnbTBhQVhlZ3ozMDU5NWhR?oc=5', 'https://news.google.com/rss/articles/CBMitgFBVV95cUxNRVZSb3ZMSnRaXzl6SzFkWHpyUkVnMXJjWkVpV2I2SU9fMmJHWjhkUzFEN0RuY0p5R2lVVk9LaVZ1RHF5SEgwcUJGb29HaDk2R2lRaDFlQnpPNE1mMDBRQlA3NlhLQmhoYWlnc2sxSkJaemJLdUE2LVl4N1NZQXU1YXJZZEwyaklUX3MwSTZhVTdLZ3dkYnFzRzc0TXIzSFhJOUVxN2Z3aU5GMjdWN3NqQ0VmVG9Pdw?oc=5', 'https://news.google.com/rss/articles/CBMinAFBVV95cUxQYjlfTzFOeHdaMnRMMk12SkM2cWZiYXUzZUtBSWhMaVZfeFE0bDZ6MEtUWTRzZ3NrZGdRczUtNnRQR29xNHdCQVhMZEVMY0VWT1o0SFAzdFhhOG5YTVdfUlNlRUJQM2pTTl9OczZwNmxDWTRFRmh2TjBqd1BvTTRoTDNybmpNTFlEbWRJZWdsSGhYMEJCX2JhOWszQ0w?oc=5', 'https://news.google.com/rss/articles/CBMizwFBVV95cUxQZmlYLVpFV3NyQlEwWlVFVnpfYnNhZEFsaWJ6VkdZUG5icnVzMVBkdXk5ZFlORGhKNTl5MDdsR2FBTlZHTzFKQk9uTWtXczRBaHB0YzFDRElESUNtR1hrN1R0QUlNVW80MDh0YVFhSUxKUHYyczRIekYtcDRNR0ZXbm9kTy1UX3NuV1R1YlFIaUVlVVFnRThkb1JpbHhaMnF3eDdTMExQX0V5TXYtcGRYeTFLUkE0WUsydmdwUDhKdEVZNm9xdVZIWmVaOTBYT2vSAc8BQVVfeXFMUGZpWC1aRVdzckJRMFpVRVZ6X2JzYWRBbGlielZHWVBuYnJ1czFQZHV5OWRZTkRoSjU5eTA3bEdhQU5WR08xSkJPbk1rV3M0QWhwdGMxQ0RJRElDbUdYazdUdEFJTVVvNDA4dGFRYUlMSlB2MnM0SHpGLXA0TUdGV25vZE8tVF9zbldUdWJRSGlFZVVRZ0U4ZG9SaWx4WjJxd3g3UzBMUF9FeU12LXBkWHkxS1JBNFlLMnZncFA4SnRFWTZvcXVWSFplWjkwWE9r?oc=5', 'https://news.google.com/rss/articles/CBMi8AFBVV95cUxOSUlUUE1fVXJPcWdfVUJkSGtvUUJiWEk1b0h1MTgzdGJmSFU5dHZpd29WajdtU0l5N1V2VWlseVZfWkVNOFVRZVJYOTRuSDhIWWlKR0l0a2dRSktZV1hteUgtVDA3Y0o0ZHhWOHlMUVZ4MnEyUmI1YjNSc1laeXBzVW1OdENQVy0tNUsyc3lOYXpBY0FHaXlWN2ZjazkxNzB1TUhick9wVU1XcVUwMTR0eDhQVGRDcndlaVNjQUhkMl9TZDJjMlJLa1REa3JPRTZfRVQzdVUtWUM0NXgyaHBrVUhzWHVPekt5QnVLdFdkY18?oc=5'], 
                'article_date': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'Thu, 09 Oct 2025 16:45:17 GMT', 'Tue, 30 Sep 2025 07:00:00 GMT', 'Tue, 14 Oct 2025 11:29:00 GMT', 'Tue, 14 Oct 2025 14:04:12 GMT', 'Tue, 14 Oct 2025 09:41:51 GMT', 'Tue, 14 Oct 2025 07:08:03 GMT', 'Mon, 13 Oct 2025 11:07:32 GMT', 'Tue, 14 Oct 2025 09:47:55 GMT', 'Mon, 13 Oct 2025 08:10:55 GMT', 'Mon, 13 Oct 2025 14:30:13 GMT', 'Tue, 14 Oct 2025 11:32:50 GMT', 'Tue, 14 Oct 2025 08:00:36 GMT', 'Mon, 13 Oct 2025 11:25:26 GMT', 'Mon, 13 Oct 2025 22:09:41 GMT', 'Mon, 13 Oct 2025 15:34:49 GMT', 'Mon, 13 Oct 2025 10:11:14 GMT', 'Wed, 24 Sep 2025 07:00:00 GMT', 'Mon, 14 Jul 2025 07:00:00 GMT', 'Tue, 14 Oct 2025 07:36:33 GMT', 'Mon, 13 Oct 2025 12:00:00 GMT'], 
                'company_name': ['Reflection AI', 'Vercel', 'Dexory', 'KOR', 'Oqood', 'SpeakX', 'Resistant AI', 'GoodScore', 'Resistant AI', 'Prezent AI', 'DVC', 'Patchworks', 'Navan', 'BNTO', 'Climaty AI', 'Resistant AI', 'Modular', 'Lucidya', 'SpeakX.ai', 'Resistant AI'], 
                'city': [], 
                'country': [], 
                'company_decision_makers': [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []], 
                'company_decision_makers_position': [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []], 
                'funding_round': ['funding', 'AI Funding Round', 'funding round', 'Series B', 'funding', 'pre-Series B', 'Series B', 'funding', 'Series B', 'Venture', 'Fund', 'Venture', 'Funding', 'Series A', 'Funding', 'Series B', 'Venture', 'Series B', 'Venture', 'Series B'], 
                'amount_raised': ['$2 billion', '', '$165m', '', '$1mln', '$16M', '$25 Million', '$13 million', '$25M', '$30M', '$75 Million', '£5m', '$300M', '$15 Million', '$2M', '$25 Million', '$250 million', '$30 million', 'Rs 142 crore', '$25 Million'], 
                'currency': ['USD', '', 'USD', '', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'GBP', 'USD', 'USD', 'USD', 'USD', 'USD', 'USD', 'INR', 'USD'], 
                'investor_companies': [['Nvidia'], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], ['WestBridge'], []], 
                'investor_people': [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []], 
                'tags': [['AI', 'funding', 'valuation'], ['AI', 'funding', 'valuation'], ['AI', 'robot', 'tech', 'funding'], ['funding', 'Series B', 'global growth'], ['AI', 'legal solutions', 'GCC'], ['AI', 'education', 'language learning'], ['AI'], ['AI', 'credit advisory', 'fintech'], ['AI', 'funding', 'Series B'], ['AI', 'funding', 'acquisition'], ['Venture Capital', 'Fund', 'AI', 'Investment'], ['AI', 'funding', 'expansion'], ['AI', 'expense management', 'travel tech', 'platform', 'funding'], ['AI', 'styling agent', 'fashion tech', 'funding'], ['AI', 'carbon-conscious marketing', 'agentic AI', 'sustainability', 'marketing tech', 'funding'], ['AI', 'fraud detection', 'fincrime', 'financial technology', 'security', 'funding'], ['AI', 'startup', 'funding', 'Nvidia dominance'], ['AI', 'funding', 'MENA', 'Series B'], ['AI', 'English learning', 'startup', 'funding', 'EdTech'], ['AI', 'fraud detection', 'fincrime', 'Series B', 'funding']]
                }
        x = await normalize_funding_data(data)
        print(x)

    asyncio.run(main())