// companies.service.ts
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ICompany } from '../../Libs/interfaces/company.interface';
import { IPeople } from '../../Libs/interfaces/people.interface';

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
  // DEV URL
  private readonly backend_url: string = 'http://192.168.1.54:5000';
  // private readonly backend_url: string = 'http://127.0.0.1:5000'; // (for home)
  // PROD URL
  // private readonly backend_url: string = '/api';

  private http = inject(HttpClient);

  /** ✅ Fetch all companies */
  fetch_companies(): Observable<ICompany[]> {
    console.log("Fetching company data from backend...");
    return this.http.get<ICompany[]>(`${this.backend_url}/fetch-companies`);
  }

  /** ✅ Fetch single company details */
  getCompanyDetails(id: number): Observable<ICompany> {
    console.log(`Fetching company with ID ${id}`);
    return this.http.get<ICompany>(`${this.backend_url}/fetch-company-details/${id}`);
  }

  /** ✅ Export companies to Excel */
  exportCompanies(): Observable<Blob> {
    console.log("Exporting companies as Excel...");
    return this.http.get(`${this.backend_url}/export`, { responseType: 'blob' });
  }

  /** ✅ Mapper function to structure company into sections */
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
          { label: 'Internal Notes', value: company.notes || 'N/A' },
          { label: 'Created At', value: company.created_at || 'N/A' },
          { label: 'Updated At', value: company.updated_at || 'N/A' },
          ...(company.people || []).map((p: IPeople) => ({
            label: `${p.full_name} (${p.title})`,
            value: p.email || 'N/A',
          })),
        ],
      },
      {
        section: 'Scores & Metrics',
        fields: [
          { label: 'ICP Score', value: company.icp_score || 'N/A' },
          { label: 'Head-count growth (6M)', value: company.organization_headcount_six_month_growth || 'N/A' },
          { label: 'Head-count growth (12M)', value: company.organization_headcount_twelve_month_growth || 'N/A' },
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

  /** ✅ Compute summary metrics for dashboard */
  getCompanySummary(): Observable<{
    total: number;
    contacted: number;
    uncontacted: number;
    engaged: number;
    conversionRate: number;
    emailsSent: number;
  }> {
    return this.fetch_companies().pipe(
      map((companies: ICompany[]) => {
        const total = companies.length;
        const contacted = companies.filter(c =>
          (c.contacted_status || '').toLowerCase().includes('contacted')
        ).length;
        const engaged = companies.filter(c =>
          (c.contacted_status || '').toLowerCase().includes('engaged')
        ).length;
        const uncontacted = total - contacted;
        const conversionRate = total ? ((engaged / total) * 100).toFixed(1) : 0;

        // ✅ Include email sent count (from new helper)
        const emailsSent = this.calculateEmailSentFromStatus(companies);

        return {
          total,
          contacted,
          uncontacted,
          engaged,
          conversionRate: Number(conversionRate),
          emailsSent
        };
      })
    );
  }

  /** ✅ Calculate total emails sent from contacted_status */
  private calculateEmailSentFromStatus(companies: ICompany[]): number {
    // Example assumption:
    // 'Contacted' = 1 email, 'Engaged' = 2, 'Uncontacted' = 0
    // You can replace this logic with real backend data later
    let emailCount = 0;
    for (const company of companies) {
      const status = (company.contacted_status || '').toLowerCase();
      if (status.includes('contacted')) emailCount += 1;
      if (status.includes('engaged')) emailCount += 2;
    }

    // For now you said the actual backend gives 50
    return 50; // Static placeholder until backend logic is linked
  }

  /** ✅ Public method to fetch total emails sent */
  getEmailSentCount(): Observable<number> {
    return this.fetch_companies().pipe(
      map((companies: ICompany[]) => this.calculateEmailSentFromStatus(companies))
    );
  }
}
