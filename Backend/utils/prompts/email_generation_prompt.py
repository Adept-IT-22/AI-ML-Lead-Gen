def get_email_generation_prompt(company_description, first_name, company_name, trigger_type, funding_round=None, hiring_area=None):
    """
    Generates a prompt for an LLM to create a highly personalized outreach email.

    Args:
        company_description (str): Detailed description of the prospect company.
        first_name (str): Contact's first name placeholder.
        company_name (str): Company name placeholder.
        trigger_type (str): 'funding' or 'hiring'.
        funding_round (str, optional): The funding round (e.g., 'Series A'). Required if trigger_type is 'funding'.
        hiring_area (str, optional): The area/role they are hiring for (e.g., 'Data Science'). Required if trigger_type is 'hiring'.
    """

    # 1. Define the custom opening based on the trigger type
    # We use TRIPLE braces for placeholders the LLM must output (e.g., {{{company_name}}})
    # and SINGLE braces for Python variables used to construct the prompt (e.g., {funding_round}).
    if trigger_type == 'funding':
        custom_opening = f"""
            <p>Congrats to the <strong>{company_name}</strong> team on raising your **{funding_round}** round!</p>
            <p>We work with fast-growing AI/ML companies like yours to help scale operations.</p>
        """
        # Define the main focus for the Subject line and CTA (Growth/Scaling)
        growth_status = f"Funded - {funding_round}"
    
    elif trigger_type == 'hiring':
        custom_opening = f"""
            <p>I noticed <strong>{company_name}</strong> is expanding the team with roles in **{hiring_area}** — that’s exciting!</p>
            <p>As you grow, some tasks can start pulling focus from your core engineering/product roadmap.</p>
        """
        # Define the main focus for the Subject line and CTA (Hiring/Expansion)
        growth_status = f"Hiring - {hiring_area}"
    
    else:
        raise ValueError("trigger_type must be 'funding' or 'hiring'")

    # 2. Return the consolidated prompt string
    return f"""
        You are an expert Sales Development Representative (SDR) tasked with crafting a highly personalized outreach email.
        Your goal is to secure a meeting by demonstrating a specific understanding of the prospect's business and connecting it directly to the services offered by your company.

        ---
        ### **Context & Services Offered (Your Company)**
        Your company, Adept Technologies, provides **scalable support services** to AI/ML companies, specifically:
        1. **Data Solutions:** Data annotation, data labeling, data quality assurance (QA).
        2. **ML Services:** Model validation, human-in-the-loop support, specialized data collection.
        3. **Customer Engagement:** Handling complex customer interactions, filtering/qualifying leads that require human review, and analytics.
        Adept also provides afforability and speed without compromising on quality. Ensure you highlight this in your email.

        ---
        ### **Prospect Company Profile**
        The company's growth status is: **{growth_status}**
        Use the following company description to identify the core challenges, primary products, and target audience:
        {company_description}

        ---
        ### **Email Requirements**
        1. **Format:** The content must be formatted as raw HTML body content. Use the placeholders: `{{first_name}}`, `{{company_name}}`, `{{funding_round}}` (if trigger is 'funding'), and `{{hiring_area}}` (if trigger is 'hiring').
        2. **Subject Line:** Create a subject line that is relevant to the prospect's vertical *and* their growth status.
        3. **Personalization:**
            * **Crucially,** the email must mention **two (2) specific ways** Adept Technologies' services (from the list above) can directly support or enhance the prospective company's current operations.
        4. **Tone:** Professional and direct, with a congratulatory or observant opening.
        5. **Call to Action (CTA):** End with a clear, low-friction request for a quick chat.
        6. 1. **Format:** The content must be formatted as raw HTML body content with all actual values filled in (no placeholders).

        ---
        ### **Email Output Template to Follow (Adapt the content within the tags):**
        ```html
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Hello {first_name},</p>
                
                {custom_opening}
                
                <p>With your focus on [MENTION PROSPECT'S KEY PRODUCT], we see a clear fit, particularly in areas like:</p>
                <ul>
                    <li>[SPECIFIC, HIGH-VALUE SOLUTION #1]</li>
                    <li>[SPECIFIC, HIGH-VALUE SOLUTION #2]</li>
                </ul>
                
                <p>This allows your team to focus on [PROSPECT'S CORE MISSION] while we handle [TIME-CONSUMING TASK].</p>
                
                <p>Would you be open to a quick chat this week to explore how we can specifically support **{company_name}**’s next phase of growth?</p>
            </body>
        </html>
        ```
        ### Return a dictionary with the following structure:
        "subject": subject,
        "content": the above email 
    """

if __name__ == "__main__":
    desc = "Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance their sales strategies through AI-driven insights."
    fname = "mark"
    cname = "Darwin AI" # Changed to Darwin AI to match description
    ttype = "funding"
    fround = "Seed"
    
    # Example 1: Funding Prompt
    funding_prompt = get_email_generation_prompt(desc, fname, cname, ttype, funding_round=fround)
    print("--- FUNDING PROMPT ---")
    print(funding_prompt)

    # Example 2: Hiring Prompt
    ttype_hiring = "hiring"
    hiring_area = "ML Engineering"
    hiring_prompt = get_email_generation_prompt(desc, fname, cname, ttype_hiring, hiring_area=hiring_area)
    print("\n--- HIRING PROMPT ---")
    print(hiring_prompt)