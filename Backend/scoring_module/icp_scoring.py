import logging
import asyncio
import statistics
from typing import Dict
from datetime import date
from utils.icp import icp, weights
from utils.prompts.work_category_prompt import get_work_category
from scoring_module.ai_extraction import extract_work_category

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#The weighting ensures the score equals 100 for all categories put together

MAX_AGE = 10
MAX_EMPLOYEE_COUNT = 100

class ICPScorer:
    def __init__(self, icp, name, founded_year = None, employee_count = None,
                 funding_stage = None, keywords = None, 
                 people = None, phone = None, linkedin = None, website = None, country = None):
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
        self.weights = weights

    async def log_scoring_start(self, name):
        logger.info(f"ICP Scoring starting for {name}...")
        return

    async def score_age(self, founded_year: int)->int:
        if not founded_year:
            return 50
        age = date.today().year - founded_year
        for (low, high), score in self.icp["age"]:
            if low <= age <= high:
                return score
        if age > MAX_AGE:
            return 0
        return 50

    async def score_employee_count(self, employee_count: int)->int:
        if not self.employee_count:
            return 50
        for (low, high), score in self.icp["employee_count"]:
            if low <= employee_count <= high:
                return score
        if employee_count > MAX_EMPLOYEE_COUNT:
            return 0
        return 50

    async def score_funding_stage(self, funding_stage: str)->int:
        if not funding_stage:
            return 50
        else:
            return 100

    async def score_funding_amount(self, funding_amount:str)->int:
        if not funding_amount:
            return 50
        final_funding_amount = int(float(funding_amount)) / 1000000
        for (low, high), score in self.icp["funding_amount"]:
            if low <= final_funding_amount <= high:
                return score
        return 50

    async def score_growth_velocity(self, growth_velocity: str)->int:
        if not growth_velocity:
            return 50
        growth_velocity = float(growth_velocity)
        for (low, high), score in self.icp["growth_velocity"]:
            if low <= growth_velocity <= high:
                return score
            elif growth_velocity > 1.0:
                return 100
        return 50

    async def score_keywords(self, keywords: list)->dict:
        if not keywords:
            return {"final_score": 0}

        try:
            prompt = get_work_category(keywords)
            work_category_data = dict(await extract_work_category(prompt))
            specific_tasks = work_category_data.get("specific_tasks", {})
            scores = list(specific_tasks.values())
            final_score = statistics.mean(scores) * 100
            work_category_data["final_score"] = round(final_score, 1)
            return work_category_data

        except Exception as e:
            logger.error(f"Failed to extract work category from LLM: {str(e)}")
            return {"final_score": 0}

    async def score_contactability(self, people: list, linkedin: str):
        if not people and not linkedin:
            return 50

        contactability = self.icp["contactability"]

        if any(person.get("email") for person in people):
            return contactability["email"]
        elif linkedin:
            return contactability["linkedin"]

    async def score_geography(self, country):
        if not country:
            return 50
        
        countries = self.icp["geography"]
        country = country.lower().strip()
        if country in countries["north_america"] or country in countries["europe"]:
            return 100
        return 0

    async def calculate_total_score(self)->Dict[str, str | int]:
        age_score = await self.score_age(self.founded_year)
        employee_count_score = await self.score_employee_count(self.employee_count)
        funding_stage_score = await self.score_funding_stage(self.funding_stage)
        #growth_velocity_score = await self.score_growth_velocity(self.growth_velocity)
        keywords_score = await self.score_keywords(self.keywords)
        task_level = keywords_score.get("task_level") if keywords_score.get("task_level") else None
        specific_tasks = keywords_score.get("specific_tasks") if keywords_score.get("specific_tasks") else None
        final_keywords_score = keywords_score.get("final_score") if keywords_score.get("final_score") else 0
        contactability_score = await self.score_contactability(self.people, self.linkedin)
        geography_score = await self.score_geography(self.country)

        total_score = (
        (age_score * self.weights["age"]) 
        + (employee_count_score * self.weights["employee_count"])
        + (funding_stage_score * self.weights["funding_stage"]) 
        #+ (growth_velocity_score * self.weights["growth_velocity"])
        + (final_keywords_score * self.weights["keywords"]) 
        + (contactability_score * self.weights["contactability"])
        + (geography_score * self.weights["geography"])
        )

        logger.info(f"{self.name}'s total score is: {total_score}")
        return {
            "task_level": task_level,
            "specific_tasks": specific_tasks,
            "total_score": round(total_score, 1)
        }
                

if __name__ == "__main__":
    async def main():
        name = 'adept'
        founded_year = 2023
        employee_count = 10
        funding_stage = 'seed'
        keywords = ['ai', 'llm']
        people = [{'email': 'm10mathenge@gmail.com'}]
        phone = '0705548993'
        linkedin = 'linkedin.com/me'
        website = 'www.adept-techno.com'
        country = 'denmark'
        scorer = ICPScorer(icp, name, founded_year, employee_count, 
                           funding_stage, keywords, people, phone, 
                           linkedin, website, country)

        await scorer.log_scoring_start(name)
        await scorer.calculate_total_score()

    asyncio.run(main())

