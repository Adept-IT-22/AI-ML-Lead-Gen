#This function converts sets to list allowing json serialization
def convert_sets(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {a: convert_sets(b) for a, b in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets(i) for i in obj]
    else:
        return obj

if __name__ == "__main__":
    x = {'lower_data_labeling_and_annotation': {'jaccard_similarity': '0.03', 'category_score': 0.01995, 'matched_words': {'data', 'in', 'ai'}, 'base_score': 100, 'weight': 0.665}, 'lower_data_verification_and_validation': {'jaccard_similarity': '0.06', 'category_score': 0.037905, 'matched_words': {'real-time', 'software', 'ai', 'automation', 'data'}, 'base_score': 95, 'weight': 0.665}, 'lower_data_curation_and_management': {'jaccard_similarity': '0.05', 'category_score': 0.029925000000000004, 'matched_words': {'data', 'automation', 'ai', 'engineering'}, 'base_score': 90, 'weight': 0.665}, 'lower_data_processing': {'jaccard_similarity': '0.10', 'category_score': 0.053200000000000004, 'matched_words': {'real-time', 'cloud', 'ai', 'scalable', 'engineering', 'foundation', 'data', 'integration'}, 'base_score': 80, 'weight': 0.665}, 'lower_transcription_and_reporting': {'jaccard_similarity': '0.03', 'category_score': 0.0149625, 'matched_words': {'intelligence', 'real-time', 'ai'}, 'base_score': 75, 'weight': 0.665}, 'lower_workflow_and_task_automation': {'jaccard_similarity': '0.06', 'category_score': 0.027929999999999996, 'matched_words': {'production', 'ai', 'orchestration', 'automation', 'data'}, 'base_score': 70, 'weight': 0.665}, 'higher_advanced_ai_and_robotics': {'jaccard_similarity': '0.26', 'category_score': 0.021775000000000003, 'matched_words': {'vision', 'learning', 'ai', 'interface', 'language', 'in', 'embodied', 'models', 'real-time', 'platform', 'generative', 'engineering', 'robotics', 'planning', 'computer', 'orchestration', 'automation', 'skill', 'agent', 'acquisition', 'transformer', 'industrial', 'foundation', 'natural'}, 'base_score': 25, 'weight': 0.335}, 'higher_domain_specific_applications': {'jaccard_similarity': '0.06', 'category_score': 0.00402, 'matched_words': {'planning', 'ai', 'in', 'engineering', 'technology', 'development', 'data'}, 'base_score': 20, 'weight': 0.335}, 'higher_strategic_decision_making': {'jaccard_similarity': '0.05', 'category_score': 0.0025125000000000004, 'matched_words': {'intelligence', 'real-time', 'planning', 'ai', 'services'}, 'base_score': 15, 'weight': 0.335}, 'higher_security_and_compliance': {'jaccard_similarity': '0.05', 'category_score': 0.0016750000000000003, 'matched_words': {'ai', 'in', 'automation', 'data', 'integration'}, 'base_score': 10, 'weight': 0.335}, 'higher_knowledge_management_and_research': {'jaccard_similarity': '0.02', 'category_score': 0.000335, 'matched_words': {'automation', 'ai'}, 'base_score': 5, 'weight': 0.335}} 
    y = convert_sets(x)
    import json
    print(json.dumps(y, indent=2))



















