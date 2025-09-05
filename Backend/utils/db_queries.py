company_query = """
        INSERT INTO companies (apollo_id, name, website_url, linkedin_url,
                    phone, founded_year, market_cap, annual_revenue, industries,
                    estimated_num_employees, keywords, organization_headcount_six_month_growth,
                    organization_headcount_twelve_month_growth, city, state, country, short_description,
                    total_funding, technology_names, icp_score, notes, company_data_source, latest_funding_round,
                    latest_funding_amount, latest_funding_currency) VALUES ($1, $2, $3, $4, $5, $6, $7, 
                    $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25) 
            """

people_query = """
                INSERT INTO people (apollo_id, first_name, last_name, full_name,
                linkedin_url, title, email_status, headline, organization_id,
                seniority, departments, subdepartments, functions, email,
                number, notes) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16)
            """