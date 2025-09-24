import logging
import asyncio
from datetime import date
from utils.icp import icp, weights
from utils.ai_keywords import ai_keywords

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#The weighting ensures the score equals 100 for all categories put together

MAX_AGE = 10

class ICPScorer:
    def __init__(self, icp, name, founded_year = None, employee_count = None,
                 funding_stage = None, funding_amount = None, growth_velocity = None,
                 keywords = None, people = None, phone = None, linkedin = None,
                 website = None, country = None):
        self.icp = icp
        self.name = name
        self.founded_year = founded_year
        self.employee_count = employee_count
        self.funding_stage = funding_stage
        self.funding_amount = funding_amount
        self.growth_velocity = growth_velocity
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
        return 50

    async def score_funding_stage(self, funding_stage: str)->int:
        if not funding_stage:
            return 50
        for key, value in self.icp["funding_stage"].items():
             if funding_stage in key or key in funding_stage:
                 return value
        return 50

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

    async def score_keywords(self, keywords: list)->int:
        if not keywords:
            return 50

        high, medium, low = 0, 0, 0
        
        for keyword in keywords:
            normal_keyword = keyword.lower().strip()

            if normal_keyword in ai_keywords["high_signal"]:
                high += 1
            elif normal_keyword in ai_keywords["medium_signal"]:
                medium += 1
            elif normal_keyword in ai_keywords["low_signal"]:
                low += 0

        total_matches = high + medium + low
        if total_matches == 0:
            return 50

        #Weight the results
        icp_keywords = self.icp["keywords"]
        weighted_score = ((high * icp_keywords["strong_match"]) + (medium * icp_keywords["medium_match"]) + (low * icp_keywords["weak_match"])) / (high + medium + low)
        return int(weighted_score)

    async def score_contactability(self, people: list, phone: str, linkedin: str, website: str):
        if not people and not phone and not linkedin and not website:
            return 50

        total_score = 0
        contactability = self.icp["contactability"]
        if any(person.get("email") for person in people):
            total_score +=  contactability["email"]
        if phone:
            total_score += contactability["phone"]
        if linkedin:
            total_score += contactability["linkedin"]
        if website:
            total_score += contactability["website"]

        return total_score

    async def score_geography(self, country):
        if not country:
            return 50
        
        countries = self.icp["geography"]
        country = country.lower().strip()
        if country in countries["north_america"] or country in countries["europe"]:
            return 100
        return 0

    async def calculate_total_score(self):
        age_score = await self.score_age(self.founded_year)
        employee_count_score = await self.score_employee_count(self.employee_count)
        funding_stage_score = await self.score_funding_stage(self.funding_stage)
        funding_amount_score = await self.score_funding_amount(self.funding_amount)
        growth_velocity_score = await self.score_growth_velocity(self.growth_velocity)
        keywords_score = await self.score_keywords(self.keywords)
        contactability_score = await self.score_contactability(self.people, self.phone, self.linkedin, self.website)
        geography_score = await self.score_geography(self.country)

        total_score = (
        (age_score * self.weights["age"]) 
        + (employee_count_score * self.weights["employee_count"])
        + (funding_stage_score * self.weights["funding_stage"]) 
        + (funding_amount_score * self.weights["funding_amount"])
        + (growth_velocity_score * self.weights["growth_velocity"])
        + (keywords_score * self.weights["keywords"]) 
        + (contactability_score * self.weights["contactability"])
        + (geography_score * self.weights["geography"])
        )

        logger.info(f"{self.name}'s total score is: {total_score}")
        return round(total_score, 1)

if __name__ == "__main__":
    async def main():
        name = 'adept'
        founded_year = 2023
        employee_count = 10
        funding_stage = 'seed'
        funding_amount = '14000000'
        growth_velocity = '0.5'
        keywords = ['ai', 'llm']
        people = [{'email': 'm10mathenge@gmail.com'}]
        phone = '0705548993'
        linkedin = 'linkedin.com/me'
        website = 'www.adept-techno.com'
        country = 'denmark'
        scorer = ICPScorer(icp, name, founded_year, employee_count, 
                           funding_stage, funding_amount, growth_velocity, 
                           keywords, people, phone, linkedin, website, country)

        await scorer.log_scoring_start(name)
        await scorer.calculate_total_score()

    asyncio.run(main())

