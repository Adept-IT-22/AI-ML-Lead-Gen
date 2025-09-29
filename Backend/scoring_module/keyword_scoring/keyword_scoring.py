#This keyword scoring module uses the Jaccard Coefficient to analyze the set
#of company keywords vs the set of each category's (e.g. data verification)
#keywords. We'll then decide based on that, which category this company
#belongs to.

import asyncio
import logging
from typing import Dict, List
from utils.ai_keywords import marking_scheme_keywords

#Configure logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

#Our current offerings are 2x as important as hopefully future offerings
LOWER_LEVEL_WEIGHT = 0.665
HIGHER_LEVEL_WEIGHT = 0.335

class JaccardKeywordScorer:
    def __init__(self, marking_scheme_keywords):
        self.marking_scheme_keywords = marking_scheme_keywords
        self.categories = self.prepare_keyword_categories()

    #Create dictionary for categories and scores
    def prepare_keyword_categories(self)->Dict:
        logger.info("Preparing keyword categories...") 
        categories = {}

        for level_name, level_data in marking_scheme_keywords.items():
            category_weight = LOWER_LEVEL_WEIGHT if level_name.lower() == 'lower' else HIGHER_LEVEL_WEIGHT

            for category_name, category_data in level_data.items():
                keyword_set = set()

                for keyword in category_data["keywords"]:
                    keyword_set.update(keyword.lower().split())
                
                categories[f"{level_name}_{category_name}"] = {
                    "keywords": keyword_set,
                    "score": category_data["score"],
                    "original_keywords": category_data["keywords"],
                    "weight": category_weight
                }
        
        return categories

    async def jaccard_similarity(self, set1: set, set2: set)->float:
        if not set1 or not set2:
            return 0.0

        #Jaccard similarity = length of intersection of sets / length of union of sets
        set_intersection = set1.intersection(set2)
        set_union = set1.union(set2)
        jaccard_similarity = len(set_intersection) / len(set_union)

        return f"{jaccard_similarity:.2f}"

    async def score_company(self, company_keywords: List[str]):
        logger.info("Scoring company keywords...")

        #Create company keywords set
        company_keywords_set = set()
        for keyword in company_keywords:
            company_keywords_set.update(keyword.lower().split())

        category_scores = {}
        total_weighted_score = 0
        total_possible_score = 0

        for category_name, category_data in self.categories.items():
            #Calculate Jaccard similarity
            category_keywords_set = category_data.get("keywords", {})

            jaccard_similarity = await self.jaccard_similarity(
                company_keywords_set, 
                category_keywords_set
                )

            #Weight category (score * weight * jaccard similarity)
            category_score = (float(category_data["score"]) / 100.0) * float(category_data["weight"]) * float(jaccard_similarity)
            category_scores[category_name] = {
                "jaccard_similarity": jaccard_similarity,
                "category_score": category_score,
                "matched_words": company_keywords_set.intersection(category_keywords_set),
                "base_score": category_data["score"],
                "weight": category_data["weight"]
            }

            total_weighted_score += category_score
            total_possible_score += (float(category_data["score"]) / 100.0) * float(category_data["weight"])

        #Final score is weighted score div by possible score
        final_score = (total_weighted_score /total_possible_score) * 100 if total_possible_score > 0 else 0

        return {
            "final_score": final_score,
            "category_breakdown": category_scores,
            "top_matches": await self.get_top_matches(category_scores),
            "interpretation": await self.interpret_score(final_score)
        }

    #Get top 3 matches
    async def get_top_matches(self, category_scores: Dict):
        #Return top 3 categories
        return sorted(
            [(category_name, category_data["jaccard_similarity"]) for category_name, category_data in category_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

    async def interpret_score(self, score: float)->str:
        logger.info("Interpreting the score...")
        
        if score >= 0.7:
            return "EXCELLENT - Strong alignment with core offerings"
        elif score >= 0.5:
            return "GOOD - Good fit with current capabilities"
        elif score >= 0.3:
            return "MODERATE - Some alignment, mainly future potential"
        else:
            return "LOW - Minimal alignment"

if __name__ == "__main__":
    keywords = test_case = [
      "artificial intelligence",
      "ai",
      "software",
      "smbs",
      "sales automation",
      "whatsapp",
      "support automation",
      "technology, information & internet",
      "ai for customer service",
      "crm integration",
      "ai for data entry",
      "ai scalability solutions",
      "customer service ai",
      "ai for operational workflows",
      "ai for real estate leads",
      "api integration",
      "conversational ai",
      "automated data entry",
      "data security",
      "natural language processing",
      "multilingual ai",
      "ai automation",
      "ai sentiment detection",
      "ai training and tuning",
      "repetitive task automation",
      "sales process automation",
      "customer support automation",
      "customer interaction automation",
      "user experience optimization",
      "ai learning algorithms",
      "customer satisfaction",
      "business process automation",
      "ai for customer feedback",
      "software development",
      "ai chatbots",
      "ai in automotive",
      "operational efficiency",
      "localization support",
      "automotive",
      "ai for complaint resolution",
      "ai for marketing campaigns",
      "ai training data",
      "ai for multilingual support",
      "ai for customer retention",
      "ai error reduction",
      "ai in healthcare",
      "ai-powered chatbots",
      "ai response quality",
      "digital workers",
      "personalized ai interactions",
      "ai for appointment scheduling",
      "business automation tools",
      "ai for insurance claims",
      "ai for retail inventory",
      "multichannel communication",
      "ai for lead scoring",
      "ai in education",
      "ai for lead generation",
      "real estate",
      "information technology and services",
      "ai for education enrollment",
      "continuous learning ai",
      "customer engagement ai",
      "ai integration with crm",
      "data privacy compliance",
      "ai task management",
      "ai for compliance monitoring",
      "retail",
      "custom system integration",
      "ai personalization",
      "ai for sentiment analysis in calls",
      "data integration",
      "ai in retail",
      "ai for cross-selling",
      "ai model tuning",
      "education",
      "ai performance monitoring",
      "automated customer support",
      "ai in real estate",
      "ai for sales and marketing",
      "ai deployment tools",
      "ai in insurance",
      "ai for dynamic pricing",
      "healthcare",
      "ai customization",
      "ai for marketing automation",
      "ai for automotive sales",
      "insurance",
      "sentiment analysis",
      "business services",
      "ai scalability",
      "cloud ai services",
      "automated testing",
      "ai for healthcare patient management",
      "customer relationship management",
      "ai for appointment reminders",
      "ai for post-sale support",
      "ai for customer onboarding",
      "ai response accuracy",
      "workflow management",
      "ai in small business",
      "ai feedback loops",
      "ai for customer journey mapping",
      "workflow automation",
      "real-time analytics",
      "b2b",
      "e-commerce",
      "d2c",
      "services",
      "computer systems design and related services",
      "customer experience",
      "data management",
      "process optimization",
      "information technology & services",
      "saas",
      "computer software",
      "enterprise software",
      "enterprises",
      "computer & network security",
      "sales",
      "education management",
      "health care",
      "health, wellness & fitness",
      "hospital & health care",
      "crm",
      "consumer internet",
      "consumers",
      "internet"
    ]
    
    async def main():
        x = JaccardKeywordScorer(marking_scheme_keywords)
        o = await x.score_company(keywords)
        import json
        logger.info(o)

    asyncio.run(main())