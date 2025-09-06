// company-details.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export interface CompanyField {
  label: string;
  value: string;
}

export interface CompanySection {
  section: string;
  fields: CompanyField[];
}

@Injectable({
  providedIn: 'root',
})
export class CompanyService {
  private apiUrl = 'http://localhost:5000'; // Flask backend URL

  constructor(private http: HttpClient) {}

  // Fetch a single company by ID
  getCompanyDetails(id: number): Observable<CompanySection[]> {
    return this.http.get<any>(`${this.apiUrl}/companies/${id}`).pipe(
      map((company) => this.mapCompanyToSections(company))
    );
  }

  // Transform backend data into UI sections
  private mapCompanyToSections(company: any): CompanySection[] {
    return [
      {
        section: 'Identity',
        fields: [
          { label: 'Company Name', value: company.name || 'N/A' },
          { label: 'Description', value: company.short_description || 'N/A' },
          { label: 'Industry', value: (company.industries || []).join(', ') },
          { label: 'Location', value: `${company.city || ''}, ${company.country || ''}` },
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
          { label: 'Total Funding', value: company.total_funding || 'N/A' },
          { label: 'Annual Revenue', value: company.annual_revenue || 'N/A' },
        ],
      },
      {
        section: 'Contacts',
        fields: [
          { label: 'Phone', value: company.phone || 'N/A' },
          { label: 'Contacted Status', value: company.contacted_status || 'N/A' },
        ],
      },
      {
        section: 'Scores & Metrics',
        fields: [
          { label: 'ICP Score', value: company.icp_score || 'N/A' },
          { label: 'Head-count growth in 6 Months', value: company.organization_headcount_six_month_growth || 'N/A' },
          { label: 'Head-count growth in 12 Months', value: company.organization_headcount_twelve_month_growth || 'N/A' },
        ],
      },
      {
        section: 'Technologies',
        fields: [
          { label: 'Technologies Used', value: (company.technology_names || []).join(', ') },
          { label: 'Keywords', value: (company.keywords || []).join(', ') },
        ],
      },
    ];
  }
}
