#This keyword scoring module uses the Jaccard Coefficient to analyze the set
#of company keywords vs the set of each category's (e.g. data verification)
#keywords. We'll then decide based on that, which category this company
#belongs to.

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

    def jaccard_similarity(self, set1: set, set2: set)->float:
        logger.info("Doing jaccard similarity...")

        if not set1 or not set2:
            return 0.0

        #Jaccard similarity = length of intersection of sets / length of union of sets
        set_intersection = set1.intersection(set2)
        set_union = set1.union(set2)
        jaccard_similarity = len(set_intersection) / len(set_union)

        return f"{jaccard_similarity:.2f}"

    def score_company(self, company_keywords: List[str]):
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

            jaccard_similarity = self.jaccard_similarity(
                company_keywords_set, 
                category_keywords_set
                )

            #Weight category (score * weight * jaccard similarity)
            category_score = (category_data["score"]/100) * category_data["weight"] * jaccard_similarity
            category_scores[category_name] = {
                "jaccard_similarity": jaccard_similarity,
                "category_score": category_score,
                "matched_words": company_keywords_set.intersection(category_keywords_set),
                "base_score": category_data["score"],
                "weight": category_data["weight"]
            }

            total_weighted_score += category_score
            total_possible_score += (category_data["score"]/100)*category_data["weight"]

        #Final score is weighted score div by possible score
        final_score = total_weighted_score /total_possible_score if total_possible_score > 0 else 0

        return {
            "final_score": final_score,
            "category_breakdown": category_scores,
            "top_matches": self.get_top_matches(category_scores),
            "interpretation": self.interpret_score(final_score)
        }

    #Get top 3 matches
    def get_top_matches(self, category_scores: Dict):
        #Return top 3 categories
        return sorted(
            [(category_name, category_data["jaccard_similarity"]) for category_name, category_data in category_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

    def interpret_score(self, score: float)->str:
        logger.info("Interpreting the score...")
        
        if score >= 0.7:
            return "EXCELLENT - Strong alignment with core offerings"
        elif score >= 0.5:
            return "GOOD - Good fit with current capabilities"
        elif score >= 0.3:
            return "MODERATE - Some alignment, mainly future potential"
        else:
            return "LOW - Minimal alignment"