# This file contains the prompt for funding

def get_funding_extraction_prompt(combined_input_for_llm):
    return f"""
    You are an expert trained to extract funding news from news articles.
    Analyze the following group of news articles. For each article, extract the following information:
    - Article Title
    - Date of Article (format as YYYY-MM-DD if possible)
    - Company Name
    - Company City
    - Company Country
    - Company Decision Makers (as a list of strings. Include names of all identifiable decision makers for the company that's raising money.)
    - Company Decision Makers Position (the positions occupied by the company decision makers above)
    - Funding Round (e.g., Seed, Series A, Series B, Venture, Private Equity, Debt, Grant, Convertible Note, Bridge, IPO, Acquisition, etc. If not explicitly mentioned, infer based on context or leave empty string if no clear indication.)
    - Amount Raised (e.g., $10M, €5M, £2.5M. Extract the numerical value and currency symbol.)
    - Currency (e.g., USD, EUR, GBP. Infer from amount raised or context.)
    - Investor Companies (as a list of strings. Include names of all identifiable investor companies.)
    - Investor People (as a list of strings. Include names of all identifiable investor people associated with the above mentioned companies.)
    - Tags (as a list of strings, relevant to the company/funding event.)
    - Pain Points (as a list of strings. Identify specific business or technical challenges mentioned in the article, e.g., "high latency in robotics", "security vulnerabilities in code", "expert supply elasticity").
    - Original Article ID (the 'Article_ID' provided for each article in the input. This is crucial for matching results.)

    If any information on a particular field is not present or cannot be confidently extracted, return an empty string "" for string fields or an empty list [] for list fields. Do not make up information.

    **IMPORTANT:** Return a dictionary in the structure of arrays format.

    Example of desired output structure for multiple articles:
    {{
        "article_id": [0, 1],
        "title": ["Tech Startup A Secures $5M Seed Funding", "Green Energy Co. B Closes Series B Round for €10 Million"],
        "article_date": ["2024-07-25", "2025-04-12"],
        "company_name": ["Tech Startup A", "Tech Startup B"],
        "city": ["San Francisco", "Berlin"],
        "country": ["America", "Germany"],
        "company_decision_makers": [["John Doe"],["Jane Doe", "John Smith"]],
        "company_decision_makers_position": [["CEO"], ["CTO", "CEO"]]
        "funding_round": ["Seed", "Series A"],
        "amount_raised": ["$5M", "$10M"],
        "currency": ["USD", "USD"],
        "investor_companies": [["VC Firm Alpha", "Angel Investor Beta"], ["GreenTech Investments"]],
        "investor_people": [["John Doe", "John Smith"], ["Jane Doe"]],
        "tags": [["tech", "startup", "funding", "SaaS", "innovation"], ["energy", "sustainability"]],
        "painpoints": [["high latency in robotics", "safety vs speed tradeoff"], ["carbon emission reporting compliance"]]
    }}

    Articles Text:
    \"\"\"
    {combined_input_for_llm}
    \"\"\"
    """
