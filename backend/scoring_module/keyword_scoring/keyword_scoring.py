### This scoring mechanism uses a direct keyword matching approach.
### It counts how many keywords from the company's profile match the category's keywords.
### 3+ matches = 100%
### 2 matches = 75%
### 1 match = 40%
### 0 matches = 0%

#import json
#from typing import List

#class TfIdfScorer: # Kept class name for compatibility
    #def __init__(self, company_keywords, marking_scheme_keywords):
        ## Flatten phrases into single words for broader matching
        #self.company_keywords = set()
        #for k in company_keywords:
            #self.company_keywords.update(k.lower().strip().split()) # Split phrases into words
        
        #self.marking_scheme_keywords = marking_scheme_keywords

    #def score(self):
        #category_scores = {}
        #all_scores = []
        
        #for level_name, level_data in self.marking_scheme_keywords.items():
            #for category_name, category_data in level_data.items():

                ## Tokenize target keywords as well
                #target_keywords = set()
                #for k in category_data['keywords']:
                     #target_keywords.update(k.lower().strip().split())
                
                ## Find intersection
                #matched = list(self.company_keywords.intersection(target_keywords))
                #match_count = len(matched)
                
                #base_score = category_data.get('base_score', 100)
                #weight = category_data.get('weight', 1.0)

                ## Direct Match Scoring Logic
                #if match_count >= 3:
                    #match_score = 1.0
                #elif match_count == 2:
                    #match_score = 0.75
                #elif match_count == 1:
                    #match_score = 0.40
                #else:
                    #match_score = 0.0

                #category_score = match_score * base_score * weight

                #category_scores[f"{level_name}_{category_name}"] = {
                    #"match_count": match_count,
                    #"category_score": category_score,
                    #"matched_tokens": matched,
                    #"base_score": base_score,
                    #"weight": weight,
                #}

                #all_scores.append(category_score)

        ## Final score = sum of category scores
        #final_score = sum(all_scores)
        
        ## Calculate max possible score to normalize if needed, 
        ## but here we just want the raw accumulation of category points 
        ## relative to the potential total if every category was a perfect match?
        ## Actually, let's normalize it against the maximum possible score 
        ## (if every category had 3+ matches) -> 100%
        
        #max_possible_score = sum([cat.get('base_score', 100) * cat.get('weight', 1.0) for level in self.marking_scheme_keywords.values() for cat in level.values()])
        
        #if max_possible_score > 0:
            #normalized_final_score = (final_score / max_possible_score) * 100
        #else:
            #normalized_final_score = 0

        ## Cap at 100 just in case
        #normalized_final_score = min(normalized_final_score, 100)

        #top_matches = self.get_top_matches(category_scores)
        
        #return {
            #"final_score": round(normalized_final_score, 1),
            #"category_breakdown": category_scores,
            #"top_matches": top_matches,
            #"interpretation": self.interpret_score(normalized_final_score)
        #}

    ## -------------------------
    ## Helpers
    ## -------------------------
    #def get_top_matches(self, category_scores, n=3):
        ## sort by score
        #sorted_cats = sorted(
            #category_scores.items(),
            #key=lambda x: x[1]['category_score'],
            #reverse=True
        #)
        #return [[cat, f"{score['match_count']} matches"] for cat, score in sorted_cats[:n] if score['category_score'] > 0]

    #def interpret_score(self, final_score):
        #if final_score >= 60:
            #return f"HIGH - Strong alignment ({final_score:.1f}%)"
        #elif final_score >= 30:
            #return f"MEDIUM - Moderate alignment ({final_score:.1f}%)"
        #else:
            #return f"LOW - Minimal alignment ({final_score:.1f}%)"

#if __name__ == "__main__":
    #pass

from typing import List

class TfIdfScorer:  # compatibility preserved

    # Strong + weak noise filter (expanded properly)
    LOW_SIGNAL_WORDS = {
        "platform", "solution", "system", "systems",
        "app", "application", "data", "technology",
        "services", "service", "software",
        "tool", "tools", "company", "product",
        "management", "analysis", "analytics",
        "automation", "support", "intelligence",
        "real", "time", "real-time", "business",
        "and", "for", "with", "the", "of", "to"
    }

    def __init__(self, company_keywords, marking_scheme_keywords):

        # -------------------------
        # Phrase-level representation
        # -------------------------
        self.company_phrases = set(
            k.lower().strip()
            for k in company_keywords
            if k and k.strip()
        )

        # -------------------------
        # Token-level representation (cleaned)
        # -------------------------
        self.company_tokens = set()

        for phrase in self.company_phrases:
            tokens = phrase.split()
            filtered = [
                t for t in tokens
                if t not in self.LOW_SIGNAL_WORDS
            ]
            self.company_tokens.update(filtered)

        self.marking_scheme_keywords = marking_scheme_keywords

    def score(self):
        category_scores = {}
        all_scores = []
        total_match_signals = 0

        for level_name, level_data in self.marking_scheme_keywords.items():
            for category_name, category_data in level_data.items():

                # -------------------------
                # Category preparation
                # -------------------------
                category_phrases = set(
                    k.lower().strip()
                    for k in category_data["keywords"]
                    if k
                )

                category_tokens = set()
                for phrase in category_phrases:
                    tokens = phrase.split()
                    filtered = [
                        t for t in tokens
                        if t not in self.LOW_SIGNAL_WORDS
                    ]
                    category_tokens.update(filtered)

                # -------------------------
                # Matching logic
                # -------------------------
                phrase_matches = self.company_phrases.intersection(category_phrases)
                token_matches = self.company_tokens.intersection(category_tokens)

                match_count = len(phrase_matches) + len(token_matches)
                total_match_signals += match_count

                base_score = category_data.get("base_score", 100)
                weight = category_data.get("weight", 1.0)

                # -------------------------
                # Core scoring logic (FIXED)
                # -------------------------
                if phrase_matches:
                    match_score = 1.0  # strongest signal
                elif len(token_matches) >= 4:
                    match_score = 0.7
                elif len(token_matches) >= 2:
                    match_score = 0.4
                else:
                    match_score = 0.0

                raw_score = match_score * base_score * weight

                # -------------------------
                # Category guardrail
                # -------------------------
                if match_count < 2:
                    raw_score = 0  # kill weak/noise matches

                category_score = min(raw_score, base_score)

                category_scores[f"{level_name}_{category_name}"] = {
                    "match_count": match_count,
                    "phrase_matches": list(phrase_matches),
                    "token_matches": list(token_matches),
                    "category_score": category_score,
                    "base_score": base_score,
                    "weight": weight,
                }

                all_scores.append(category_score)

        # -------------------------
        # Aggregation
        # -------------------------
        final_score = sum(all_scores)

        max_possible_score = sum(
            cat.get("base_score", 100) * cat.get("weight", 1.0)
            for level in self.marking_scheme_keywords.values()
            for cat in level.values()
        )

        if max_possible_score > 0:
            normalized_final_score = (final_score / max_possible_score) * 100
        else:
            normalized_final_score = 0

        # -------------------------
        # Global noise penalty
        # -------------------------
        if total_match_signals < 3:
            normalized_final_score *= 0.5

        normalized_final_score = min(normalized_final_score, 100)

        return {
            "final_score": round(normalized_final_score, 1),
            "category_breakdown": category_scores,
            "top_matches": self.get_top_matches(category_scores),
            "interpretation": self.interpret_score(normalized_final_score),
        }

    # -------------------------
    # Helpers
    # -------------------------

    def get_top_matches(self, category_scores, n=3):
        sorted_cats = sorted(
            category_scores.items(),
            key=lambda x: x[1]["category_score"],
            reverse=True,
        )

        return [
            [cat, f"{score['match_count']} matches"]
            for cat, score in sorted_cats[:n]
            if score["category_score"] > 0
        ]

    def interpret_score(self, final_score):
        if final_score >= 60:
            return f"HIGH - Strong alignment ({final_score:.1f}%)"
        elif final_score >= 30:
            return f"MEDIUM - Moderate alignment ({final_score:.1f}%)"
        else:
            return f"LOW - Minimal alignment ({final_score:.1f}%)"

if __name__ == "__main__":
    from utils.ai_keywords import marking_scheme_keywords
    company_keywords = [
        "payment services & blockchain",
        "payment services",
        "payments",
        "consumer internet",
        "internet",
        "information technology",
        "financial inclusion solutions",
        "ai and post-humanism",
        "smart contract platform",
        "ai and digital gods",
        "predictive analytics",
        "sharding technology",
        "ai experimentation",
        "consulting",
        "ai and human-machine interaction",
        "blockchain for payments",
        "machine learning",
        "ai in art and culture",
        "smart contracts",
        "ai in customer lifecycle management",
        "ai in fraud prevention",
        "smart contract development",
        "instant payment solutions",
        "scalable blockchain",
        "agi preparedness",
        "ai and divine creation",
        "ai in risk management",
        "transaction processing",
        "ai-driven customer support",
        "scalable transaction processing",
        "hyper-localized financial solutions",
        "services",
        "ai in fraud detection",
        "ai and ethics",
        "open finance innovation",
        "experimental ai projects",
        "ai-driven media creation",
        "ai and metaphysics",
        "financial services",
        "fraud detection ai",
        "ai-powered payments",
        "ai-driven creative experiments",
        "ai in scientific exploration",
        "scalability",
        "ai consciousness projects",
        "blockchain infrastructure",
        "behavioral credit scoring",
        "ai and the universe",
        "ai in media and art",
        "ai applications in finance",
        "fraud detection",
        "customer-centric approach",
        "ai ethics in finance",
        "ai and blockchain integration",
        "ai in scientific research",
        "ai and machine learning",
        "ai in user lifecycle",
        "ai hallucinations",
        "financial solutions",
        "ai and the future of life",
        "ai in creative projects",
        "ai and symbolic interaction",
        "blockchain technology",
        "multi-raft consensus blockchain",
        "ai and human-machine symbiosis",
        "retail",
        "fintech",
        "hyperparameter optimization",
        "geospatial financial analysis",
        "data-driven financial models",
        "ai and social impact",
        "ai research and experimentation",
        "ai customer support",
        "financial transactions processing, reserve, and clearinghouse activities",
        "ai research",
        "ai and the evolution of consciousness",
        "ai in credit assessment",
        "payment network",
        "ai consciousness",
        "ai and symbiosis with humans",
        "financial technology",
        "graph networks",
        "behavioral analysis",
        "merchant payment solutions",
        "digital payment platforms",
        "ai and philosophy",
        "interplanetary payment network",
        "next-generation financial services",
        "hospitality",
        "d2c",
        "ai and future of humanity",
        "ai in scientific discovery",
        "monitoring systems",
        "customer engagement",
        "ai for risk management",
        "ai algorithms",
        "innovation",
        "disruptive economics",
        "payment processing",
        "data analytics",
        "e-commerce",
        "b2b",
        "blockchain scalability",
        "high transaction throughput",
        "data infrastructure",
        "ai in payments",
        "global payment network",
        "ai and the emergence of new gods",
        "ai ethics",
        "ml feature selection",
        "software development",
        "experimental game development",
        "user experience",
        "open-source blockchain",
        "credit scoring",
        "geospatial analysis",
        "open-source financial solutions",
        "blockchain solutions",
        "instant payments",
        "customer support automation",
        "data-centric approach",
        "geospatial data analysis",
        "evolutionary algorithms",
        "user behavior analytics",
        "transaction scalability",
        "real-time transaction monitoring",
        "digital financial solutions",
        "fintech innovation",
        "artificial general intelligence",
        "user lifetime value modeling",
        "churn prediction",
        "workflow optimization",
        "anomaly detection",
        "transparent financial transactions",
        "peer-to-peer payments",
        "low transaction fees",
        "evm compatibility",
        "tech-driven financial services",
        "secure payment systems",
        "customizable payment solutions",
        "data-driven insights",
        "conversational ai",
        "next-generation transaction network",
        "decentralized finance",
        "merchant analytics",
        "behavioral credit assessment",
        "dynamic risk assessment",
        "automated customer interactions",
        "high-performance payments",
        "digital currency solutions",
        "interplanetary financial network",
        "personalized financial services",
        "financial data analytics",
        "ai-enhanced security",
        "finance",
        "education",
        "consumers",
        "information technology & services",
        "enterprise software",
        "enterprises",
        "computer software",
        "artificial intelligence",
        "computer & network security",
        "finance technology",
        "leisure, travel & tourism",
        "ux"
    ]

    scorer = TfIdfScorer(company_keywords, marking_scheme_keywords)
    score = scorer.score()
    print(score)