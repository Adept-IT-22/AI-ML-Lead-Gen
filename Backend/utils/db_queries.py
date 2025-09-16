company_query = """
        INSERT INTO companies (apollo_id, name, website_url, linkedin_url,
                    phone, founded_year, market_cap, annual_revenue, industries,
                    estimated_num_employees, keywords, organization_headcount_six_month_growth,
                    organization_headcount_twelve_month_growth, city, state, country, short_description,
                    total_funding, technology_names, icp_score, notes, company_data_source, latest_funding_round,
                    latest_funding_amount, latest_funding_currency) VALUES ($1, $2, $3, $4, $5, $6, $7, 
                    $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25) 
                ON CONFLICT (apollo_id) DO NOTHING
            """

people_query = """
                INSERT INTO people (apollo_id, first_name, last_name, full_name,
                linkedin_url, title, email_status, headline, organization_id,
                seniority, departments, subdepartments, functions, email,
                number, notes) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16)
                ON CONFLICT (apollo_id) DO NOTHING
            """

normalized_master_query = """
        INSERT INTO normalized_master (type, source, link, title, city, country, tags) 
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (link) DO NOTHING
                RETURNING id
                """

normalized_funding_query = """
        INSERT INTO normalized_funding (master_id, company_name, company_decision_makers,
                company_decision_makers_position, funding_round, amount_raised,
                currency, investor_companies, investor_people) VALUES ($1, $2, $3,
                $4, $5, $6, $7, $8, $9)
                """

normalized_hiring_query = """
        INSERT INTO normalized_hiring (master_id, company_name, company_decision_makers,
                company_decision_makers_position, job_roles, hiring_reasons)
                VALUES ($1, $2, $3, $4, $5, $6)
                """ 

normalized_events_query = """
        INSERT INTO normalized_events (master_id, event_id, event_summary, event_is_online,
                event_organizer_id) VALUES ($1, $2, $3, $4, $5)
                """