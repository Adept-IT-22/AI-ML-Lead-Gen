import json
from utils.ai_keywords import marking_scheme_keywords

def get_work_category(company_name, company_keywords, scoring_dictionary):
    """
    Generates a prompt for an LLM to categorize and score a company's keywords.

    Args:
        company_name (str): The name of the company.
        company_keywords (list): A list of keywords associated with the company.
        scoring_dictionary (dict): The dictionary containing keywords and their scores.

    Returns:
        str: The fully formatted prompt for the LLM.
    """
    prompt_template = """
        You are a highly analytical and experienced AI business strategist. Your task is to analyze a company's business keywords, categorize them as "lower" or "higher" level tasks, and calculate a total score for each category.

        Here is the dictionary of keywords and their corresponding scores:

        {marking_scheme_keywords}

        ---

        **Company Name:** {company_name}
        **Company Keywords:**
        {company_keywords_list}

        **Instructions:**
        1.  Analyze the provided "Company Keywords" for {company_name}.
        2.  For each keyword, determine if it falls under a "lower" or a "higher" level category in the provided dictionary.
        3.  **IMPORTANT:** If a keyword from the company's list does not have an exact match, find the **closest matching keyword** in the dictionary to determine its category and score.
        4.  Calculate a **total score** for all keywords mapped to the "lower" level tasks.
        5.  Calculate a **total score** for all keywords mapped to the "higher" level tasks.
        6.  Generate a JSON object that strictly follows this schema. Do not include any additional text or explanation.

        **JSON Schema:**
        {{
        "company_name": "{company_name}",
        "keyword_analysis": {{
            "lower_level_tasks": {{
            "total_score": null,
            "matching_keywords": [
                {{ "keyword": "...", "score": null }}
            ],
            "inferred_categories": [
                "..."
            ]
            }},
            "higher_level_tasks": {{
            "total_score": null,
            "matching_keywords": [
                {{ "keyword": "...", "score": null }}
            ],
            "inferred_categories": [
                "..."
            ]
            }}
        }}
        }}
    """
    formatted_prompt = prompt_template.format(
        company_name=company_name,
        company_keywords_list=json.dumps(company_keywords, indent=2),
        marking_scheme_keywords=json.dumps(scoring_dictionary, indent=2)
    )
    return formatted_prompt
