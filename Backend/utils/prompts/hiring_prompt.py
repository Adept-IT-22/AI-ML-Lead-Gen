#This file contains the hiring prompt

def get_hiring_extraction_prompt(combined_input_for_llm: str):
    return f"""
        You are an expert trained to extract hiring-related insights from news articles.
        Analyze the following group of news articles. For each article, extract the following information:

        - Article ID (original ID provided in the input)
        - Article Title  
        - Date of Article (format as YYYY-MM-DD if possible)  
        - Company Name  
        - Company Website (if mentioned or can be confidently inferred)  
        - Company City  
        - Company Country  
        - Company Decision Makers (as a list of strings. Include names of all identifiable decision makers or hiring managers mentioned.)  
        - Job Roles (as a list of strings. Extract the specific job roles, positions, or departments the company is hiring for, e.g., "software engineer", "data scientist", "marketing", "product design".)  
        - Hiring Reason (e.g., "expansion", "product launch", "new funding", "team growth", etc. If not clear, leave as an empty string "")  
        - Tags (as a list of strings relevant to the article or company, such as "AI", "healthtech", "startup", "remote", "growth")  

        If any field is missing or not confidently extractable, return an empty string `""` for single values or an empty list `[]` for lists. Do **not** make up any data.

        **IMPORTANT:** Return the results in dictionary format using the **Structure of Arrays** pattern.

        Example of the desired output structure:
        {{
            "article_id": [4435439, 4578992],
            "article_title": [
                "AI Startup X Announces Plans to Hire 100 Engineers",
                "Fintech Y Expands European Team Amid Growth"
            ],
            "article_date": ["2025-07-25", "2025-07-27"],
            "company_name": ["AI Startup X", "Fintech Y"],
            "company_website": ["aix.com", "fintechy.eu"],
            "company_city": ["New York", "Paris"],
            "company_country": ["USA", "France"],
            "company_decision_makers": [["Jane Doe"], ["Pierre Martin", "Sophie Durand"]],
            "job_roles": [["software engineer", "machine learning"], ["sales", "business development"]],
            "hiring_reason": ["expansion", "new product launch"],
            "tags": [["AI", "startup", "engineering"], ["fintech", "europe", "growth"]],
        }}
        Articles Text:
        \"\"\"
        {combined_input_for_llm}
        \"\"\"
        """