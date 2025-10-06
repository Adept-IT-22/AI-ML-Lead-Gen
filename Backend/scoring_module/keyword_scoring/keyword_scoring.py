# This scoring mechanism successfully uses TF-IDF and Cosine Similarity 
# to gauge alignment. It treats the company's keywords as a Query Document 
# and each category in the marking scheme as a separate Target Document.

# First, it calculates the Term Frequency (TF) for every word in the company's
# Query Document and in each Target Document. Simultaneously, it calculates 
# the global Inverse Document Frequency (IDF) for every unique word across 
# all documents to measure word rarity.

# Next, it computes the final TF-IDF score for every word in both the Query 
# and Target vectors by multiplying its TF by its IDF weight.

# Finally, it uses Cosine Similarity to mathematically compare the resulting 
# company keyword vector against each category's keyword vector, yielding 
# a similarity score (a decimal between 0.0 and 1.0) that represents the 
# topical fit.


# TO CHANGE:
# ===========
# 1. Calculate only the services we offer.
# 2. Add a 'Future Services' category.

import math
import json
from collections import Counter

class TfIdfScorer:
    def __init__(self, company_keywords, marking_scheme_keywords):
        self.company_keywords = company_keywords
        self.company_keywords_doc = " ".join(q.lower() for q in company_keywords)
        self.marking_scheme_keywords = marking_scheme_keywords

    # -------------------------
    # TF-IDF helpers
    # -------------------------
    def compute_tf(self, doc):
        tf = Counter(doc.split())
        total_terms = sum(tf.values())
        return {word: count/total_terms for word, count in tf.items()}

    def compute_idf(self, docs):
        N = len(docs)
        idf = {}
        all_words = set(word for doc in docs for word in doc.split())
        for word in all_words:
            df = sum(1 for doc in docs if word in doc.split())
            idf[word] = math.log((N+1)/(df+1)) + 1
        return idf

    def compute_tfidf(self, company_keywords, docs):
        idf = self.compute_idf(docs + [company_keywords])
        tfidf_docs = []
        for doc in docs:
            tf = self.compute_tf(doc)
            tfidf_docs.append({word: tf[word]*idf[word] for word in tf})
        
        tf_company_keywords = self.compute_tf(company_keywords)
        tfidf_company_keywords = {word: tf_company_keywords[word]*idf[word] for word in tf_company_keywords}
        
        return self.cosine_similarities(tfidf_company_keywords, tfidf_docs)

    def cosine_similarities(self, company_keywords_vec, doc_vecs):
        def dot(v1, v2):
            return sum(v1.get(w,0)*v2.get(w,0) for w in set(v1)|set(v2))
        def norm(v):
            return math.sqrt(sum(val*val for val in v.values()))
        
        q_norm = norm(company_keywords_vec)
        sims = []
        for doc_vec in doc_vecs:
            d_norm = norm(doc_vec)
            if q_norm*d_norm == 0:
                sims.append(0.0)
            else:
                sims.append((dot(company_keywords_vec, doc_vec)/(q_norm*d_norm)))
        return sims

    # -------------------------
    # Core scoring
    # -------------------------
    def score(self):
        category_scores = {}
        all_scores = []

        for level_name, level_data in self.marking_scheme_keywords.items():
            for category_name, category_data in level_data.items():
                category_keywords = category_data['keywords']
                base_score = category_data.get('base_score', 100)
                weight = category_data.get('weight', 1.0)

                # Compute similarity
                sims = self.compute_tfidf(self.company_keywords_doc, category_keywords)
                avg_sim = sum(sims) / len(sims) if sims else 0.0

                # Matched keywords
                matched = [q for q in self.company_keywords if q in category_keywords]

                # Category score
                category_score = avg_sim * base_score * weight

                category_scores[f"{level_name}_{category_name}"] = {
                    "tf_idf": f"{avg_sim:.2f}",  
                    "category_score": category_score,
                    "matched_words": matched,
                    "base_score": base_score,
                    "weight": weight,
                }

                all_scores.append(category_score)

        # Final score = sum of category scores
        final_score = sum(all_scores)

        return {
            "final_score": round(final_score, 1),
            "category_breakdown": category_scores,
            "top_matches": self.get_top_matches(category_scores),
            "interpretation": self.interpret_score(final_score)
        }

    # -------------------------
    # Helpers
    # -------------------------
    def get_top_matches(self, category_scores, n=3):
        # sort by similarity
        sorted_cats = sorted(
            category_scores.items(),
            key=lambda x: float(x[1]['tf_idf']),
            reverse=True
        )
        return [(cat, score['tf_idf']) for cat, score in sorted_cats[:n]]

    def interpret_score(self, final_score):
        if final_score >= 70:
            return "HIGH - Strong alignment"
        elif final_score >= 40:
            return "MEDIUM - Moderate alignment"
        else:
            return "LOW - Minimal alignment"


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    from utils.ai_keywords import marking_scheme_keywords

    company_keywords = [
        "software development",
      "ai for patient data",
      "ai for kol insights",
      "research automation",
      "ai for life sciences consulting",
      "pharma-specific ai",
      "ai for medical literature",
      "secure ai deployment",
      "data analysis tools",
      "biotech ai",
      "workflow automation",
      "ai for primary research",
      "drug discovery",
      "security frameworks",
      "ai citations",
      "data integration",
      "data security",
      "data coverage",
      "ai for clinical research",
      "clinical trial review",
      "clinical workflows",
      "industry-specific ai",
      "ai for life sciences",
      "on-prem deployment",
      "knowledge management",
      "pharmaceuticals",
      "pharma ai",
      "ai for drug safety",
      "ai knowledge base",
      "knowledge hydration",
      "clinical data analysis",
      "real-world data",
      "data privacy",
      "ai for pharma",
      "ai for rwd analysis",
      "healthcare technology",
      "compliance in ai",
      "drug development ai",
      "medical research automation",
      "biotechnology",
      "medical research",
      "knowledge graphs",
      "biopharma ai",
      "natural language processing",
      "ai for biotechs",
      "b2b",
      "consulting",
      "services",
      "research and development in the physical, engineering, and life sciences",
      "pharma",
      "life sciences",
      "security",
      "market research",
      "machine learning",
      "biotech",
      "business intelligence",
      "project management",
      "information technology & services",
      "enterprise software",
      "enterprises",
      "computer software",
      "computer & network security",
      "medical",
      "artificial intelligence",
      "analytics",
      "productivity"
    ]
    
    scorer = TfIdfScorer(company_keywords, marking_scheme_keywords)
    results = scorer.score()
    print(json.dumps(results, indent=2))

