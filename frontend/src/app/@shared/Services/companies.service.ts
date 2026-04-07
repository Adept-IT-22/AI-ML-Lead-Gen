// companies.service.ts
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ICompany } from '../../Libs/interfaces/company.interface';
import { IPeople } from '../../Libs/interfaces/people.interface';
import { IEmail } from '../../Libs/interfaces/email.interface';
import { environment } from '../../../environments/environment.prod';

interface CompanyField {
  label: string;
  value: string | number;
}

export interface CompanySection {
  section: string;
  fields: CompanyField[];
}

@Injectable({
  providedIn: 'root'
})
export class CompaniesService {
  private readonly backend_url: string = `${environment.API_URL}`

  private http = inject(HttpClient);

  // Fetch all companies (with embedded people array)
  fetch_companies(): Observable<ICompany[]> {
    console.log("Fetching company data from backend...");
    return this.http.get<ICompany[]>(`${this.backend_url}/fetch-companies`);
  }

  // ✅ Fetch single company details (also has people)
  getCompanyDetails(id: number): Observable<ICompany> {
    console.log(`Fetching company with ID ${id}`);
    return this.http.get<ICompany>(`${this.backend_url}/fetch-company-details/${id}`);
  }

  // ✅ Export companies to Excel
  exportCompanies(): Observable<Blob> {
    console.log("Exporting companies as Excel...");
    return this.http.get(`${this.backend_url}/export`, {
      responseType: 'blob'  // <-- important to handle file download
    });
  }

  viewSentEmails(company_id: number): Observable<IEmail> {
    console.log("Still fetching emails...")
    return this.http.get<IEmail>(`${this.backend_url}/view-sent-emails/${company_id}`);
  }

  // ✅ Mapper function to structure company into sections
  mapCompanyToSections(company: ICompany): CompanySection[] {
    return [
      {
        section: 'Identity',
        fields: [
          { label: 'Company Name', value: company.name || 'N/A' },
          { label: 'Description', value: company.short_description || 'N/A' },
          { label: 'Industry', value: (company.industries || []).join(', ') || 'N/A' },
          { label: 'Location', value: `${company.city || ''}, ${company.state || ''}, ${company.country || ''}` },
          { label: 'Status', value: company.status || 'N/A' },
          { label: 'Data Source', value: company.company_data_source || 'N/A' },
        ],
      },
      {
        section: 'Online Presence',
        fields: [
          { label: 'Website', value: company.website_url || 'N/A' },
          { label: 'LinkedIn', value: company.linkedin_url || 'N/A' },
        ],
      },
      {
        section: 'Company Profile',
        fields: [
          { label: 'Year Founded', value: company.founded_year || 'N/A' },
          { label: 'Number of Employees', value: company.estimated_num_employees || 'N/A' },
          { label: 'Annual Revenue', value: company.annual_revenue || 'N/A' },
          { label: 'Market Cap', value: company.market_cap || 'N/A' },
          { label: 'Total Funding', value: company.total_funding || 'N/A' },
          { label: 'Latest Round', value: company.latest_funding_round || 'N/A' },
          { label: 'Latest Funding Amount', value: company.latest_funding_amount || 'N/A' },
          { label: 'Currency', value: company.latest_funding_currency || 'N/A' },
        ],
      },
      {
        section: 'Contacts',
        fields: [
          { label: 'Phone', value: company.phone || 'N/A' },
          { label: 'Contacted Status', value: company.contacted_status || 'N/A' },
          { label: 'Created At', value: company.created_at || 'N/A' },
          { label: 'Updated At', value: company.updated_at || 'N/A' },
          // Loop through people array and map them into fields
          ...((company.people || []).map((p: IPeople) => ({
            label: `${p.full_name || 'N/A'} (${p.title || 'N/A'})`,
            value: p.email || 'N/A'
          })))
        ],
      },
      {
        section: 'Scores & Metrics',
        fields: [
          { label: 'ICP Score', value: company.icp_score || 'N/A' },
          { label: 'Head-count growth (6M)', value: company.organization_headcount_six_month_growth || 'N/A' },
          { label: 'Head-count growth (12M)', value: company.organization_headcount_twelve_month_growth || 'N/A' },
          {
            label: 'Services To Provide',
            value: (() => {
              if (!company.top_matches) return 'N/A';
              try {
                const arr = JSON.parse(company.top_matches);
                if (Array.isArray(arr) && arr.length > 0) {
                  return arr.map((item: any[]) => item[0]).join(', ');
                }
                return 'N/A'
              } catch {
                return 'N/A'
              }
            })()
          },
          { label: 'Alignment', value: company.interpretation || 'N/A' }
        ],
      },
      {
        section: 'Technologies',
        fields: [
          { label: 'Technologies Used', value: (company.technology_names || []).join(', ') || 'N/A' },
          { label: 'Keywords', value: (company.keywords || []).join(', ') || 'N/A' },
        ],
      },
    ];
  }
}
