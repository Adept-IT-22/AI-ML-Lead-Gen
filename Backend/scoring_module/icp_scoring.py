import logging
import asyncio
import statistics
from typing import Dict
from datetime import date
from utils.icp import icp, weights
from utils.prompts.work_category_prompt import get_work_category
from utils.ai_keywords import marking_scheme_keywords
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
        #Here we will select keywords and feed them to an LLM to be scored.
        #We'll then take results for lower level work, divide them against
        #the total score for lower level work and multiply by 100

        if not keywords:
            return {"final_score": 0}
        
        #Get total score for lower level work
        lower_level_scores = []
        lower_level_work = marking_scheme_keywords.get("lower")
        for lower_categories in lower_level_work.values():
            for lower_scores in lower_categories.values():
                lower_level_scores.append(lower_scores)
        total_lower_level_scores = sum(lower_level_scores)

        #Get total score for higher level work
        higher_level_scores = []
        higher_level_work = marking_scheme_keywords.get("higher")
        for higher_categories in higher_level_work.values():
            for higher_scores in higher_categories.values():
                higher_level_scores.append(higher_scores)
        total_higher_level_scores = sum(higher_level_scores)

        #Feed the LLM the keywords and get results
        try:
            prompt = get_work_category(self.name, keywords, marking_scheme_keywords)
            work_category_data = dict(await extract_work_category(prompt))
            total_score = work_category_data.get("keyword_analysis", {}).get("lower_level_tasks", {}).get("total_score", None)
            final_score = (total_score/total_lower_level_scores) * 100
            work_category_data["final_score"] = round(final_score, 1)

            #Get level of work that company does
            level_of_work_score = total_higher_level_scores / total_lower_level_scores
            if level_of_work_score <= 1:
                level_of_work = "lower"
            else:
                level_of_work = "higher"

            work_category_data["task_level"] = level_of_work

            return work_category_data

        except Exception as e:
            logger.error(f"❌ Failed to extract work category from LLM: {str(e)}")
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
        specific_tasks = keywords_score.get("keyword_analysis", {}).get("lower_level_tasks", {}).get("inferred_categories", []) 
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

        logger.info(f"{keywords_score}, {final_keywords_score}")
        logger.info(f"{self.name}'s total score is: {total_score}")
        logger.info(f"""
            task_level: {task_level},
            specific_tasks: {specific_tasks},
            total_score: {round(total_score, 1)}
            """
            )
            
        
        return {
            "task_level": task_level,
            "specific_tasks": specific_tasks,
            "total_score": round(total_score, 1)
        }
                

if __name__ == "__main__":
    async def main():
        name = 'adept'
        founded_year = 2023
        employee_count = 23
        funding_stage = 'seed'
        people = [
      {
        "email": "maor@getleo.ai",
        "full_name": "Maor Farid",
        "title": "Co-Founder & CEO"
      }
    ]
        keywords = [
      "ai",
      "generative ai",
      "engineering",
      "design",
      "cad",
      "cad software",
      "technology, information & internet",
      "generative design for mechanics",
      "automated design review",
      "ai for engineering standards compliance",
      "ai-driven component sourcing",
      "digital engineering",
      "computer software",
      "engineering knowledge management",
      "engineering services",
      "natural language processing",
      "design automation",
      "mechanical engineering",
      "engineering documentation",
      "component retrieval",
      "engineering calculations",
      "product design",
      "legacy data harnessing in engineering",
      "product development",
      "machine learning",
      "mechanical design ideation ai",
      "product design software",
      "multimodal input processing",
      "automated calculations",
      "product lifecycle management",
      "ai for product development",
      "engineering knowledge base",
      "engineering knowledge centralization",
      "automated design suggestions",
      "design brainstorming",
      "large mechanical model",
      "engineering data integration",
      "design decision support",
      "product design optimization ai",
      "engineering collaboration tools",
      "design concept generation",
      "cad plugin",
      "mechanical engineering assistant",
      "product specifications",
      "part search engine",
      "engineering decision support",
      "industrial design",
      "component search",
      "multi-modal engineering ai",
      "ai-powered engineering design",
      "cad integration",
      "ai in cad",
      "product data management",
      "digital twin integration",
      "legacy data utilization",
      "ai engineering assistant",
      "structural analysis",
      "context-aware engineering answers",
      "ai for complex structural analysis",
      "multimodal inputs",
      "real-time answers",
      "ai for early-stage development",
      "b2b",
      "services",
      "enterprise software",
      "enterprises",
      "information technology & services",
      "artificial intelligence",
      "mechanical or industrial engineering"
    ]
        phone = '0705548993'
        linkedin = 'linkedin.com/me'
        website = 'www.adept-techno.com'
        country = 'United States'
        scorer = ICPScorer(icp, name, founded_year, employee_count, 
                           funding_stage, keywords, people, phone, 
                           linkedin, website, country)

        await scorer.log_scoring_start(name)
        await scorer.calculate_total_score()

    asyncio.run(main())

