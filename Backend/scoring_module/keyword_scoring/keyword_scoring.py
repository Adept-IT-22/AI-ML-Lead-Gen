## This scoring mechanism uses a direct keyword matching approach.
## It counts how many keywords from the company's profile match the category's keywords.
## 3+ matches = 100%
## 2 matches = 75%
## 1 match = 40%
## 0 matches = 0%

import json
from typing import List

class TfIdfScorer: # Kept class name for compatibility
    def __init__(self, company_keywords, marking_scheme_keywords):
        # Flatten phrases into single words for broader matching
        self.company_keywords = set()
        for k in company_keywords:
            self.company_keywords.update(k.lower().strip().split()) # Split phrases into words
        
        self.marking_scheme_keywords = marking_scheme_keywords

    def score(self):
        category_scores = {}
        all_scores = []
        
        for level_name, level_data in self.marking_scheme_keywords.items():
            for category_name, category_data in level_data.items():

                # Tokenize target keywords as well
                target_keywords = set()
                for k in category_data['keywords']:
                     target_keywords.update(k.lower().strip().split())
                
                # Find intersection
                matched = list(self.company_keywords.intersection(target_keywords))
                match_count = len(matched)
                
                base_score = category_data.get('base_score', 100)
                weight = category_data.get('weight', 1.0)

                # Direct Match Scoring Logic
                if match_count >= 3:
                    match_score = 1.0
                elif match_count == 2:
                    match_score = 0.75
                elif match_count == 1:
                    match_score = 0.40
                else:
                    match_score = 0.0

                category_score = match_score * base_score * weight

                category_scores[f"{level_name}_{category_name}"] = {
                    "match_count": match_count,
                    "category_score": category_score,
                    "matched_tokens": matched,
                    "base_score": base_score,
                    "weight": weight,
                }

                all_scores.append(category_score)

        # Final score = sum of category scores
        final_score = sum(all_scores)
        
        # Calculate max possible score to normalize if needed, 
        # but here we just want the raw accumulation of category points 
        # relative to the potential total if every category was a perfect match?
        # Actually, let's normalize it against the maximum possible score 
        # (if every category had 3+ matches) -> 100%
        
        max_possible_score = sum([cat.get('base_score', 100) * cat.get('weight', 1.0) for level in self.marking_scheme_keywords.values() for cat in level.values()])
        
        if max_possible_score > 0:
            normalized_final_score = (final_score / max_possible_score) * 100
        else:
            normalized_final_score = 0

        # Cap at 100 just in case
        normalized_final_score = min(normalized_final_score, 100)

        top_matches = self.get_top_matches(category_scores)
        
        return {
            "final_score": round(normalized_final_score, 1),
            "category_breakdown": category_scores,
            "top_matches": top_matches,
            "interpretation": self.interpret_score(normalized_final_score)
        }

    # -------------------------
    # Helpers
    # -------------------------
    def get_top_matches(self, category_scores, n=3):
        # sort by score
        sorted_cats = sorted(
            category_scores.items(),
            key=lambda x: x[1]['category_score'],
            reverse=True
        )
        return [[cat, f"{score['match_count']} matches"] for cat, score in sorted_cats[:n] if score['category_score'] > 0]

    def interpret_score(self, final_score):
        if final_score >= 60:
            return f"HIGH - Strong alignment ({final_score:.1f}%)"
        elif final_score >= 30:
            return f"MEDIUM - Moderate alignment ({final_score:.1f}%)"
        else:
            return f"LOW - Minimal alignment ({final_score:.1f}%)"

if __name__ == "__main__":
    pass
