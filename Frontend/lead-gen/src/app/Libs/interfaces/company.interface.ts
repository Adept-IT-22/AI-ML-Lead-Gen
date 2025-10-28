import { IPeople } from "./people.interface"; 

export interface ICompany {
  annual_revenue: string | null;
  apollo_id: string;
  city: string;
  company_data_source: string;
  contacted_status: string;
  country: string | null;
  created_at: string | null;
  estimated_num_employees: number | null;
  founded_year: number| null;
  icp_score: string | null;
  id: number;
  industries: string[] | null;
  interpretation: string | null;
  keywords: string[] | null;
  latest_funding_amount: string | null;
  latest_funding_currency: string | null;
  latest_funding_round: string | null;
  linkedin_url: string | null;
  market_cap: string | null;
  name: string;
  notes: string | null;
  organization_headcount_six_month_growth: string | null;
  organization_headcount_twelve_month_growth: string | null;
  people?: IPeople[];
  phone: string | null;
  short_description: string | null;
  source_link: string | null;
  state: string | null;
  status: string | null;
  technology_names: string[] | null;
  top_matches: string | null;
  total_funding: string | null;
  updated_at: string | null;
  website_url: string | null;
  [key: string]: any;
}

