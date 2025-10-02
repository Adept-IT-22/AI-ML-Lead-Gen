import math
import json
from collections import Counter

class TfIdfScorer:
    def __init__(self, query, marking_scheme_keywords):
        self.query = query
        self.query_doc = " ".join(q.lower() for q in query)
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

    def compute_tfidf(self, query, docs):
        idf = self.compute_idf(docs + [query])
        tfidf_docs = []
        for doc in docs:
            tf = self.compute_tf(doc)
            tfidf_docs.append({word: tf[word]*idf[word] for word in tf})
        
        tf_query = self.compute_tf(query)
        tfidf_query = {word: tf_query[word]*idf[word] for word in tf_query}
        
        return self.cosine_similarities(tfidf_query, tfidf_docs)

    def cosine_similarities(self, query_vec, doc_vecs):
        def dot(v1, v2):
            return sum(v1.get(w,0)*v2.get(w,0) for w in set(v1)|set(v2))
        def norm(v):
            return math.sqrt(sum(val*val for val in v.values()))
        
        q_norm = norm(query_vec)
        sims = []
        for doc_vec in doc_vecs:
            d_norm = norm(doc_vec)
            if q_norm*d_norm == 0:
                sims.append(0.0)
            else:
                sims.append((dot(query_vec, doc_vec)/(q_norm*d_norm)))
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

                # Compute sims
                sims = self.compute_tfidf(self.query_doc, category_keywords)
                avg_sim = sum(sims) / len(sims) if sims else 0.0

                # Matched keywords
                matched = [q for q in self.query if q in category_keywords]

                # Category score
                category_score = avg_sim * base_score * weight

                category_scores[f"{level_name}_{category_name}"] = {
                    "jaccard_similarity": f"{avg_sim:.2f}",  # keep format consistent
                    "category_score": category_score,
                    "matched_words": matched,
                    "total_words": len(category_keywords),
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
            key=lambda x: float(x[1]['jaccard_similarity']),
            reverse=True
        )
        return [(cat, score['jaccard_similarity']) for cat, score in sorted_cats[:n]]

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

    query = [ "artificial intelligence",
    "contingency based it recruiting",
      "it recruiting",
      "it staffing",
      "it consulting",
      "talent delivery",
      "it contracting",
      "managed services",
      "it salary",
      "technology",
      "it talent assessment",
      "network security specialists",
      "executive search",
      "information technology and services",
      "it talent sourcing platforms",
      "full-time hiring",
      "tech talent analytics",
      "tech hiring trends",
      "technology recruitment",
      "digital twin specialists",
      "tech talent market insights",
      "cybersecurity",
      "tech recruitment",
      "tech talent pool",
      "tech employment",
      "tech event series",
      "tech industry",
      "it staffing solutions",
      "embedded systems staffing",
      "devsecops recruitment",
      "industry-specific recruitment",
      "ux design",
      "tech talent retention",
      "security operations staffing",
      "talent acquisition",
      "tech community",
      "market intelligence",
      "software development",
      "data engineering recruitment",
      "cloud security specialists",
      "ai and machine learning talent",
      "technology hiring strategies",
      "cloud infrastructure",
      "time-to-fill",
      "tech workforce development",
      "tech talent management",
      "hardware engineering staffing",
      "local networks",
      "embedded systems",
      "candidate satisfaction",
      "it talent pipeline development",
      "security incident response staffing",
      "iot automation talent",
      "cloud platform engineers",
      "tech talent onboarding",
      "tech industry leaders",
      "robotics engineering jobs",
      "tech talent networks",
      "contract staffing",
      "direct hire",
      "enterprise it solutions",
      "tech talent sourcing tools",
      "tech industry partnerships",
      "tech talent pipeline",
      "staffing and recruiting",
      "product ux/ui recruitment",
      "tech talent consulting",
      "tech roles",
      "specialized tech recruiters",
      "industry expertise",
      "tech talent engagement",
      "it workforce solutions",
      "it talent sourcing",
      "remote tech jobs",
      "tech trends",
      "specialized recruiters",
      "tech talent development",
      "startup hiring",
      "tech innovation",
      "technology talent",
      "cybersecurity talent",
      "grc compliance staffing",
      "it recruitment process",
      "enterprise clients",
      "tech sectors",
      "product management",
      "recruitment solutions",
      "tech workforce",
      "it project staffing",
      "enterprise cybersecurity staffing",
      "technology sector expertise",
      "tech industry growth",
      "tech community engagement",
      "ai security professionals",
      "robotics",
      "data science",
      "digital transformation staffing",
      "ai data scientists",
      "cyber red team recruitment",
      "tech disciplines",
      "it staffing technology",
      "tech talent acquisition",
      "it staffing market",
      "it workforce planning",
      "b2b",
      "consulting",
      "services",
      "management consulting services",
      "infrastructure",
      "project management",
      "staffing & recruiting",
      "information technology & services",
      "management consulting",
      "enterprise software",
      "enterprises",
      "computer software",
      "internet infrastructure",
      "internet",
      "embedded hardware & software",
      "hardware",
      "mechanical or industrial engineering",
      "productivity"
      ]

    scorer = TfIdfScorer(query, marking_scheme_keywords)
    results = scorer.score()
    print(json.dumps(results, indent=2))
