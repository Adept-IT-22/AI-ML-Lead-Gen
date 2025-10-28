## This scoring mechanism successfully uses TF-IDF and Cosine Similarity 
## to gauge alignment. It treats the company's keywords as a Query Document 
## and each category in the marking scheme as a separate Target Document.

## First, it calculates the Term Frequency (TF) for every word in the company's
## Query Document and in each Target Document. Simultaneously, it calculates 
## the global Inverse Document Frequency (IDF) for every unique word across 
## all documents to measure word rarity.

## Next, it computes the final TF-IDF score for every word in both the Query 
## and Target vectors by multiplying its TF by its IDF weight.

## Finally, it uses Cosine Similarity to mathematically compare the resulting 
## company keyword vector against each category's keyword vector, yielding 
## a similarity score (a decimal between 0.0 and 1.0) that represents the 
## topical fit.


## TO CHANGE:
## ===========
## 1. Calculate only the services we offer.
## 2. Add a 'Future Services' category.

import math
import json
from collections import Counter

class TfIdfScorer:
    def __init__(self, company_keywords, marking_scheme_keywords):
        self.company_keywords = company_keywords
        # Create the company document (query document)
        self.company_keywords_doc = " ".join(q.lower() for q in company_keywords)
        self.marking_scheme_keywords = marking_scheme_keywords

    # -------------------------
    # TF-IDF helpers
    # -------------------------
    def compute_tf(self, doc):
        """Computes term frequency (TF) for a single document."""
        tf = Counter(doc.split())
        total_terms = sum(tf.values())
        # Use log-normalization to prevent score explosion from high frequency words
        return {word: 1 + math.log(count / total_terms) if total_terms > 0 else 0 
                for word, count in tf.items()}

    def compute_idf(self, all_docs):
        """Computes inverse document frequency (IDF) across all documents."""
        N = len(all_docs)
        idf = {}
        # Get all unique words across all documents
        all_words = set(word for doc in all_docs for word in doc.split())
        
        for word in all_words:
            # Document frequency: count how many documents contain the word
            df = sum(1 for doc in all_docs if word in doc.split())
            # Standard smooth IDF: log((N+1)/(df+1)) + 1 to prevent division by zero
            idf[word] = math.log((N+1)/(df+1)) + 1
        return idf

    def compute_tfidf_single(self, query_doc, target_doc, all_docs):
        """Computes TF-IDF vector for Query and Target, then returns Cosine Similarity."""
        # 1. Compute IDF across all documents (Query + Target + All other Categories)
        idf = self.compute_idf(all_docs)

        # 2. Compute TF-IDF for Query (Company)
        tf_query = self.compute_tf(query_doc)
        tfidf_query = {word: tf_query[word] * idf.get(word, 1.0) for word in tf_query}

        # 3. Compute TF-IDF for Target (Category)
        tf_target = self.compute_tf(target_doc)
        tfidf_target = {word: tf_target[word] * idf.get(word, 1.0) for word in tf_target}

        # 4. Compute Cosine Similarity
        return self._cosine_similarity(tfidf_query, tfidf_target)

    def _cosine_similarity(self, v1, v2):
        """Calculates the cosine similarity between two TF-IDF vectors."""
        def dot(v1, v2):
            return sum(v1.get(w, 0.0) * v2.get(w, 0.0) for w in set(v1) | set(v2))
        
        def norm(v):
            return math.sqrt(sum(val * val for val in v.values()))
        
        dot_product = dot(v1, v2)
        v1_norm = norm(v1)
        v2_norm = norm(v2)
        
        if v1_norm == 0.0 or v2_norm == 0.0:
            return 0.0
        
        return dot_product / (v1_norm * v2_norm)

    # -------------------------
    # Core scoring
    # -------------------------
    def score(self, filter_by_services=True):
        category_scores = {}
        all_scores = []
        
        # 1. Create a list of ALL documents (company doc + all consolidated category docs)
        # This is required for correct global IDF calculation
        all_category_docs = []
        for level_data in self.marking_scheme_keywords.values():
            for category_data in level_data.values():
                # CONSOLIDATION: Join all keywords into a single document string
                target_doc = " ".join(category_data['keywords']).lower()
                all_category_docs.append(target_doc)

        all_docs_for_idf = all_category_docs + [self.company_keywords_doc]

        for level_name, level_data in self.marking_scheme_keywords.items():
            for category_name, category_data in level_data.items():
                
                # REQUEST 1: Calculate only the services we offer (using a new 'is_service' flag)
                is_service = category_data.get('is_service', True) 
                if filter_by_services and not is_service:
                    continue

                category_keywords = category_data['keywords']
                # Consolidation is key to fixing the score: one massive document per category
                target_doc = " ".join(category_keywords).lower()
                
                base_score = category_data.get('base_score', 100)
                weight = category_data.get('weight', 1.0)

                # Compute single similarity score against the consolidated document
                # Note: We pass all_docs_for_idf to ensure global IDF calculation is correct
                avg_sim = self.compute_tfidf_single(
                    self.company_keywords_doc, 
                    target_doc, 
                    all_docs_for_idf
                )

                # Category score is now based on this single, meaningful similarity
                category_score = avg_sim * base_score * weight

                # Matched keywords (simpler term matching for display)
                company_tokens = set(self.company_keywords_doc.split())
                category_tokens = set(target_doc.split())
                matched = list(company_tokens.intersection(category_tokens))

                category_scores[f"{level_name}_{category_name}"] = {
                    "tf_idf": f"{avg_sim:.4f}",  # Increased precision for debugging
                    "category_score": category_score,
                    "matched_tokens": matched,
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
            "interpretation": self.interpret_score(final_score, len(all_scores))
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

    def interpret_score(self, final_score, num_categories):
        # Use a percentage-based interpretation based on the potential max score
        max_possible_score = num_categories * 100 # Assuming base_score=100 and weight=1.0
        percentage = (final_score / max_possible_score) * 100 if max_possible_score > 0 else 0

        if percentage >= 60:
            return f"HIGH - Strong alignment ({percentage:.1f}%)"
        elif percentage >= 30:
            return f"MEDIUM - Moderate alignment ({percentage:.1f}%)"
        else:
            return f"LOW - Minimal alignment ({percentage:.1f}%)"# This fixed scorer treats each category's ENTIRE set of keywords
# as a single, consolidated document for a meaningful TF-IDF comparison.

import math
import json
from collections import Counter

class TfIdfScorer:
    def __init__(self, company_keywords, marking_scheme_keywords):
        self.company_keywords = company_keywords
        # Create the company document (query document)
        self.company_keywords_doc = " ".join(q.lower() for q in company_keywords)
        self.marking_scheme_keywords = marking_scheme_keywords

    # -------------------------
    # TF-IDF helpers
    # -------------------------
    def compute_tf(self, doc):
        """Computes term frequency (TF) for a single document."""
        tf = Counter(doc.split())
        total_terms = sum(tf.values())
        # Use log-normalization to prevent score explosion from high frequency words
        return {word: 1 + math.log(count / total_terms) if total_terms > 0 else 0 
                for word, count in tf.items()}

    def compute_idf(self, all_docs):
        """Computes inverse document frequency (IDF) across all documents."""
        N = len(all_docs)
        idf = {}
        # Get all unique words across all documents
        all_words = set(word for doc in all_docs for word in doc.split())
        
        for word in all_words:
            # Document frequency: count how many documents contain the word
            df = sum(1 for doc in all_docs if word in doc.split())
            # Standard smooth IDF: log((N+1)/(df+1)) + 1 to prevent division by zero
            idf[word] = math.log((N+1)/(df+1)) + 1
        return idf

    def compute_tfidf_single(self, query_doc, target_doc, all_docs):
        """Computes TF-IDF vector for Query and Target, then returns Cosine Similarity."""
        # 1. Compute IDF across all documents (Query + Target + All other Categories)
        idf = self.compute_idf(all_docs)

        # 2. Compute TF-IDF for Query (Company)
        tf_query = self.compute_tf(query_doc)
        tfidf_query = {word: tf_query[word] * idf.get(word, 1.0) for word in tf_query}

        # 3. Compute TF-IDF for Target (Category)
        tf_target = self.compute_tf(target_doc)
        tfidf_target = {word: tf_target[word] * idf.get(word, 1.0) for word in tf_target}

        # 4. Compute Cosine Similarity
        return self._cosine_similarity(tfidf_query, tfidf_target)

    def _cosine_similarity(self, v1, v2):
        """Calculates the cosine similarity between two TF-IDF vectors."""
        def dot(v1, v2):
            return sum(v1.get(w, 0.0) * v2.get(w, 0.0) for w in set(v1) | set(v2))
        
        def norm(v):
            return math.sqrt(sum(val * val for val in v.values()))
        
        dot_product = dot(v1, v2)
        v1_norm = norm(v1)
        v2_norm = norm(v2)
        
        if v1_norm == 0.0 or v2_norm == 0.0:
            return 0.0
        
        return dot_product / (v1_norm * v2_norm)

    # -------------------------
    # Core scoring
    # -------------------------
    def score(self, filter_by_services=True):
        category_scores = {}
        all_scores = []
        
        # 1. Create a list of ALL documents (company doc + all consolidated category docs)
        # This is required for correct global IDF calculation
        all_category_docs = []
        for level_data in self.marking_scheme_keywords.values():
            for category_data in level_data.values():
                # CONSOLIDATION: Join all keywords into a single document string
                target_doc = " ".join(category_data['keywords']).lower()
                all_category_docs.append(target_doc)

        all_docs_for_idf = all_category_docs + [self.company_keywords_doc]

        for level_name, level_data in self.marking_scheme_keywords.items():
            for category_name, category_data in level_data.items():
                
                # REQUEST 1: Calculate only the services we offer (using a new 'is_service' flag)
                is_service = category_data.get('is_service', True) 
                if filter_by_services and not is_service:
                    continue

                category_keywords = category_data['keywords']
                # Consolidation is key to fixing the score: one massive document per category
                target_doc = " ".join(category_keywords).lower()
                
                base_score = category_data.get('base_score', 100)
                weight = category_data.get('weight', 1.0)

                # Compute single similarity score against the consolidated document
                # Note: We pass all_docs_for_idf to ensure global IDF calculation is correct
                avg_sim = self.compute_tfidf_single(
                    self.company_keywords_doc, 
                    target_doc, 
                    all_docs_for_idf
                )

                # Category score is now based on this single, meaningful similarity
                category_score = avg_sim * base_score * weight

                # Matched keywords (simpler term matching for display)
                company_tokens = set(self.company_keywords_doc.split())
                category_tokens = set(target_doc.split())
                matched = list(company_tokens.intersection(category_tokens))

                category_scores[f"{level_name}_{category_name}"] = {
                    "tf_idf": f"{avg_sim:.4f}",  # Increased precision for debugging
                    "category_score": category_score,
                    "matched_tokens": matched,
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
            "interpretation": self.interpret_score(final_score, len(all_scores))
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

    def interpret_score(self, final_score, num_categories):
        # Use a percentage-based interpretation based on the potential max score
        max_possible_score = num_categories * 100 # Assuming base_score=100 and weight=1.0
        percentage = (final_score / max_possible_score) * 100 if max_possible_score > 0 else 0

        if percentage >= 60:
            return "HIGH - Strong alignment"
        elif percentage >= 30:
            return "MEDIUM - Moderate alignment"
        else:
            return "LOW - Minimal alignment"

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    from utils.ai_keywords import marking_scheme_keywords

    company_keywords = [
      "integration",
      "api",
      "cloud",
      "hr data",
      "saas",
      "enterprise software",
      "b2b",
      "automation",
      "gdpr compliance",
      "hris",
      "user provisioning",
      "software development",
      "no-code platform",
      "automated provisioning",
      "information technology and services",
      "user-friendly dashboard",
      "employee data integrations",
      "data synchronization",
      "employee data management",
      "cloud marketplace",
      "custom fields support",
      "data compliance",
      "data security standards",
      "api connectors",
      "real-time data sync",
      "workflow automation",
      "data enrichment",
      "hr and it automation",
      "automated employee provisioning",
      "data governance",
      "integration platform",
      "hipaa compliance",
      "data security",
      "data mapping",
      "multi-source data consolidation",
      "error management",
      "data audit trail",
      "integration error alerts",
      "predictive data mapping",
      "employee lifecycle data",
      "predictive analytics",
      "employee records automation",
      "soc2 compliance",
      "ai-driven insights",
      "vendor requirement matching",
      "no-code integration",
      "error handling",
      "security and compliance",
      "custom calculated fields",
      "cloud connectors",
      "human resources",
      "vendor integration",
      "hr data integration",
      "vendor data sync",
      "services",
      "computer systems design and related services",
      "digital transformation",
      "business intelligence",
      "computer software",
      "information technology & services",
      "enterprises",
      "computer & network security",
      "analytics"
    ]
    
    # Run the scorer with the fixed logic and service filtering
    scorer = TfIdfScorer(company_keywords, marking_scheme_keywords)
    results = scorer.score(filter_by_services=False) # Showing all categories for demonstration
    print("\n--- RESULTS WITH FIXED LOGIC (All Categories) ---")
    print(json.dumps(results, indent=2))
    
    # Running again with service filtering enabled (data_labeling_and_annotation will be excluded)
    results_filtered = scorer.score(filter_by_services=True)
    print("\n--- RESULTS WITH FIXED LOGIC (Services Only) ---")
    print(json.dumps(results_filtered, indent=2))

