from utils.email_prompts import email_prompts

def get_email_generation_prompt(company_description, first_name, company_name, trigger_type, sequence_number, funding_round=None, hiring_area=None, painpoints=None):
    """
    Generates a prompt for an LLM to create a highly personalized outreach email.

    Args:
        company_description (str): Detailed description of the prospect company.
        first_name (str): Contact's first name placeholder.
        company_name (str): Company name placeholder.
        trigger_type (str): 'funding' or 'hiring'.
        funding_round (str, optional): The funding round (e.g., 'Series A'). Required if trigger_type is 'funding'.
        hiring_area (str, optional): The area/role they are hiring for (e.g., 'Data Science'). Required if trigger_type is 'hiring'.
        painpoints (list, optional): List of specific pain points identified for the company.
    """

    # 1. Define the custom opening based on the trigger type
    # We use TRIPLE braces for placeholders the LLM must output (e.g., {{{company_name}}})
    # and SINGLE braces for Python variables used to construct the prompt (e.g., {funding_round}).
    if trigger_type == 'funding':
        custom_opening = f"""
            <p>Congrats to the <strong>{company_name}</strong> team on raising your <strong>{funding_round}</strong> round!</p>
        """
        # Define the main focus for the Subject line and CTA (Growth/Scaling)
        growth_status = f"Funded - {funding_round}"
    
    elif trigger_type == 'hiring':
        custom_opening = f"""
            <p>I noticed <strong>{company_name}</strong> is expanding the team with roles in <strong>{hiring_area}</strong> — that’s exciting!</p>
        """
        # Define the main focus for the Subject line and CTA (Hiring/Expansion)
        growth_status = f"Hiring - {hiring_area}"
    
    else:
        raise ValueError("trigger_type must be 'funding' or 'hiring'")

    # 2. Return the consolidated prompt string
    prompt_template = email_prompts.get(sequence_number)

    return prompt_template.format(
        first_name=first_name if first_name else None,
        company_name=company_name if company_name else None,
        company_description=company_description if company_description else None,
        growth_status=growth_status if growth_status else None,
        custom_opening=custom_opening if custom_opening else None,
        hiring_area=hiring_area if hiring_area else None,
        painpoints="\n".join([f"- {p}" for p in painpoints]) if painpoints else "- general scaling bottlenecks"
    )

if __name__ == "__main__":
    desc = "Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance their sales strategies through AI-driven insights."
    fname = "mark"
    cname = "Darwin AI" # Changed to Darwin AI to match description
    ttype = "funding"
    fround = "Seed"
    seq_no = 2
    
    # Example 1: Funding Prompt
    funding_prompt = get_email_generation_prompt(desc, fname, cname, ttype, seq_no, funding_round=fround)
    print("--- FUNDING PROMPT ---")
    print(funding_prompt)

    # Example 2: Hiring Prompt
    ttype_hiring = "hiring"
    hiring_area = "ML Engineering"
    hiring_prompt = get_email_generation_prompt(desc, fname, cname, ttype_hiring, seq_no, hiring_area=hiring_area)
    print("\n--- HIRING PROMPT ---")
    print(hiring_prompt)