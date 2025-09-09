import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CompaniesService, CompanySection } from '../../Services/companies.service';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card'; 
import { ICompany } from '../../../Libs/interfaces/company.interface';

@Component({
  selector: 'app-company-details',
  imports: [CommonModule, MatCardModule],
  standalone: true,
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {
  companyId!: number;
  companyDetails: ICompany | null = null;

  expandedFields: { [key: string]: boolean } = {};

  constructor(private route: ActivatedRoute, private companiesService: CompaniesService) {}

  companyEntries: { key: string, value: any }[] = [];
  companySections: {
    title: string;
    entries: { key: string; value: any }[];
  }[] = [];

  ngOnInit(): void {
    this.companyId = Number(this.route.snapshot.paramMap.get('id'));

    this.companiesService.getCompanyDetails(this.companyId).subscribe({
      next: (details) => {
        this.companyDetails = details;
        this.companiesService.getCompanyDetails(this.companyId).subscribe({
          next: (details) => {
            this.companyDetails = details;

            this.companySections = [
              {
                title: 'Basic Info',
                entries: [
                  { key: 'Name', value: details.name },
                  { key: 'Description', value: details.short_description },
                  { key: 'Website', value: details.website_url },
                  { key: 'LinkedIn', value: details.linkedin_url },
                  { key: 'Phone', value: details.phone },
                  { key: 'Location', value: `${details.city}, ${details.state}, ${details.country}` },
                  { key: 'Founded', value: details.founded_year },
                  { key: 'Industries', value: details.industries?.join(', ') }
                ]
              },
              {
                title: 'Growth & Funding',
                entries: [
                  { key: 'Funding Round', value: details.latest_funding_round },
                  { key: 'Funding Amount', value: details.latest_funding_amount },
                  { key: 'Currency', value: details.latest_funding_currency },
                  { key: 'Total Funding', value: details.total_funding },
                  { key: 'Market Cap', value: details.market_cap },
                  { key: 'Employees', value: details.estimated_num_employees },
                  { key: '6-Month Growth', value: details.organization_headcount_six_month_growth },
                  { key: '12-Month Growth', value: details.organization_headcount_twelve_month_growth }
                ]
              },
              {
                title: 'People',
                entries: details.people?.map((p: any) => ({
                  key: p.full_name,
                  value: `${p.full_name}\n (${p.email})`
                })) || []
              },
              {
                title: 'Technologies & Keywords',
                entries: [
                  { key: 'Technologies', value: details.technology_names?.join(', ') },
                  { key: 'Keywords', value: details.keywords?.join(', ') }
                ]
              },
              {
                title: 'Meta / Status',
                entries: [
                  { key: 'ID', value: details.id },
                  { key: 'Status', value: details.status },
                  { key: 'Source', value: details.company_data_source },
                  { key: 'Contacted', value: details.contacted_status },
                  { key: 'ICP Score', value: details.icp_score },
                  { key: 'Created At', value: details.created_at },
                  { key: 'Updated At', value: details.updated_at },
                  { key: 'Notes', value: details.notes }
                ]
              }
            ];
          }
        });
        this.companyEntries = Object.entries(details).map(([key, value]) => ({ key, value }));
      },
      error: (err) => {
        console.error('Error fetching company details:', err);
      }
    });
  }

  // ✅ Toggle read more/less
  toggleField(label: string): void {
    this.expandedFields[label] = !this.expandedFields[label];
  }

  // ✅ Truncate long text to first 120 chars
  truncate(value: string, maxLength: number = 120): string {
    if (!value) return 'N/A';
    return value.length > maxLength ? value.substring(0, maxLength) + '...' : value;
  }

  isExpanded(label: string): boolean {
    return !!this.expandedFields[label];
  }

  isLink(value: any): boolean {
  if (!value) return false;
  return typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'));
}

}
