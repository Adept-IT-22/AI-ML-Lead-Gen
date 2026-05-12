import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import date
from utils.icp import icp, weights
from utils.ai_keywords import marking_scheme_keywords
from scoring_module.keyword_scoring.keyword_scoring import TfIdfScorer

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_AGE = 10
MAX_EMPLOYEE_COUNT = 100

class ICPScorer:
    def __init__(self, icp, name, founded_year=None, employee_count=None,
                 funding_stage=None, keywords=None,
                 people=None, phone=None, linkedin=None, website=None,
                 country=None, industry=None):
        self.icp = icp
        self.name = name
        self.founded_year = founded_year
        self.employee_count = employee_count
        self.funding_stage = funding_stage
        self.keywords = keywords or []
        self.people = people or []
        self.phone = phone
        self.linkedin = linkedin
        self.website = website
        self.country = country
        self.industry = industry
        self.weights = weights

    async def log_scoring_start(self, name):
        logger.info(f"ICP Scoring starting for {name}...")

    async def score_age(self, founded_year: int) -> Optional[int]:
        if not founded_year:
            return None
        age = date.today().year - founded_year
        for (low, high), score in self.icp["age"]:
            if low <= age <= high:
                return score
        if age > MAX_AGE:
            return 0
        return None

    async def score_employee_count(self, employee_count: int) -> Optional[int]:
        if not employee_count:
            return None
        for (low, high), score in self.icp["employee_count"]:
            if low <= employee_count <= high:
                return score
        if employee_count > MAX_EMPLOYEE_COUNT:
            return 0
        return None

    async def score_funding_stage(self, funding_stage: str) -> Optional[int]:
        if not funding_stage:
            return None
        normalised = funding_stage.lower().strip().replace(" ", "_").replace("-", "_")
        return self.icp["funding_stage"].get(normalised, 0)

    async def score_keywords(self, keywords: list) -> dict:
        tfidf_scorer = TfIdfScorer(keywords, marking_scheme_keywords)
        return tfidf_scorer.score()

    async def score_geography(self, country: str) -> Optional[int]:
        if not country:
            return None
        country = country.lower().strip()
        for tier, (country_set, score) in self.icp["geography"].items():
            if country in country_set:
                return score
        return 0

    async def score_industry(self, industry: str) -> Optional[int]:
        if not industry:
            return None
        industry = industry[0].lower().strip()
        for tier, (industry_set, score) in self.icp["industry"].items():
            if any(ind in industry for ind in industry_set):
                return score
        return 0

    async def calculate_total_score(self) -> Dict[str, Any]:
        age_score = await self.score_age(self.founded_year)
        employee_count_score = await self.score_employee_count(self.employee_count)
        funding_stage_score = await self.score_funding_stage(self.funding_stage)
        industry_score = await self.score_industry(self.industry)
        geography_score = await self.score_geography(self.country)

        keywords_score = await self.score_keywords(self.keywords)
        category_breakdown = keywords_score.get("category_breakdown") or None
        top_matches = keywords_score.get("top_matches") or None
        interpretation = keywords_score.get("interpretation") or None
        final_keywords_score = keywords_score.get("final_score")

        # Map each dimension to its score and weight
        dimension_results = {
            "geography":      (geography_score,      self.weights["geography"]),
            "funding_stage":  (funding_stage_score,  self.weights["funding_stage"]),
            "employee_count": (employee_count_score,  self.weights["employee_count"]),
            "age":            (age_score,             self.weights["age"]),
            "industry":       (industry_score,        self.weights["industry"]),
            "keywords":       (final_keywords_score,  self.weights["keywords"]),
        }

        weighted_sum = 0.0
        active_weight_sum = 0.0

        for dimension, (score, weight) in dimension_results.items():
            if score is not None:
                weighted_sum += score * weight
                active_weight_sum += weight

        if active_weight_sum == 0:
            total_score = 0.0
        else:
            total_score = weighted_sum / active_weight_sum

        logger.info(f"{self.name}'s total score is: {round(total_score, 2)}")
        return {
            "geography_score": geography_score,
            "funding_stage_score": funding_stage_score,
            "employee_count_score": employee_count_score,
            "age_score": age_score,
            "industry_score": industry_score,
            "final_keywords_score": final_keywords_score,
            "category_breakdown": category_breakdown,
            "top_matches": top_matches,
            "interpretation": interpretation,
            "total_score": round(total_score, 2)
        }


if __name__ == "__main__":
    async def main():
        from services.db_service import fetch_company_details

        fetched_company = await fetch_company_details(468)

        name = fetched_company.get('name')
        founded_year = fetched_company.get('founded_year')
        employee_count = fetched_company.get('estimated_num_employees')
        funding_stage = fetched_company.get('latest_funding_round')
        keywords = fetched_company.get('keywords')
        people = fetched_company.get('people', [])
        phone = fetched_company.get('phone', '')
        linkedin = [people_dict.get('linkedin_url', '') for people_dict in people][0] if people else None
        website = fetched_company.get('website_url', '')
        country = fetched_company.get('country', '')
        industry = fetched_company.get('industries', '')

        scorer = ICPScorer(icp, name, founded_year, employee_count,
                           funding_stage, keywords, people, phone,
                           linkedin, website, country, industry)

        await scorer.log_scoring_start(name)
        print(await scorer.calculate_total_score())

    asyncio.run(main())