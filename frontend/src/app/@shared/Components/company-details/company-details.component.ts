import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CompaniesService, CompanySection } from '../../Services/companies.service';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ICompany } from '../../../Libs/interfaces/company.interface';
import { LoaderComponent } from '../loader/loader.component';
import { NotesComponent } from '../notes/notes.component';
import { ButtonComponent } from "../button/button.component";

@Component({
  selector: 'app-company-details',
  standalone: true,
  imports: [CommonModule, MatCardModule, LoaderComponent, NotesComponent, ButtonComponent],
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {
  companyId!: number;
  companyDetails: (ICompany & {
    newRemarks?: string;
    previousRemarks?: string;
  }) | null = null; // ✅ extends type safely

  expandedFields: { [key: string]: boolean } = {};

  companySections: {
    title: string;
    entries: { key: string; value: any; expandable?: boolean }[];
  }[] = [];

  constructor(
    private route: ActivatedRoute,
    private companiesService: CompaniesService
  ) { }

  ngOnInit(): void {
    this.companyId = Number(this.route.snapshot.paramMap.get('id'));

    this.companiesService.getCompanyDetails(this.companyId).subscribe({
      next: (details) => {
        this.companyDetails = details;

        this.companySections = [
          {
            title: 'Identity',
            entries: [
              { key: 'Company Name', value: details.name },
              { key: 'Description', value: details.short_description, expandable: true },
              { key: 'Industry', value: details.industries?.join(', ') },
              { key: 'Location', value: `${details.city}, ${details.state}, ${details.country}` },
              { key: 'Service', value: details.service },
              { key: 'Pain points', value: details.painpoints || 'N/A' }
            ]
          },
          {
            title: 'Online Presence',
            entries: [
              { key: 'Website', value: details.website_url },
              { key: 'LinkedIn', value: details.linkedin_url },
              { key: 'Source Article', value: details.source_link }
            ]
          },
          {
            title: 'Company Profile',
            entries: [
              { key: 'Year Founded', value: details.founded_year },
              { key: 'Number of Employees', value: details.estimated_num_employees },
              { key: 'Total Funding', value: this.formatNumber(details.total_funding) },
              { key: 'Annual Revenue', value: this.formatNumber(details.annual_revenue) },
              {
                key: 'Services Needed',
                value: (() => {
                  if (!details.top_matches) return 'N/A';
                  try {
                    const arr = JSON.parse(details.top_matches);
                    if (Array.isArray(arr) && arr.length > 0) {
                      return arr
                        .map((item: any[]) =>
                          item[0]
                            .replace(/^lower_/, '')
                            .replace(/^higher_/, '')
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, (c: string) => c.toUpperCase())
                        )
                        .join(', ');
                    }
                    return 'N/A';
                  } catch {
                    return 'N/A';
                  }
                })()
              },
              { key: 'Potential Fit', value: details.interpretation }
            ]
          },
          {
            title: 'Contacts',
            entries: [
              ...(details.people?.map((p: any) => ({
                key: p.title || 'Contact',
                value: `${p.full_name || 'N/A'} | ${p.email || 'N/A'} | ${p.linkedin_url || 'N/A'}`
              })) || []),
              { key: 'Company Phone', value: details.phone },
              { key: 'Contacted Status', value: details.contacted_status }
            ]
          },
          {
            title: 'Funding, Scores & Metrics',
            entries: [
              { key: 'ICP Score', value: details.icp_score },
              { key: 'Latest Funding Round', value: details.latest_funding_round },
              { key: 'Latest Funding Amount', value: this.formatNumber(details.latest_funding_amount) },
              { key: 'Latest Funding Currency', value: details.latest_funding_currency },
              { key: 'Head-count growth in 6 Months', value: details.organization_headcount_six_month_growth },
              { key: 'Head-count growth in 12 Months', value: details.organization_headcount_twelve_month_growth }
            ]
          },
          {
            title: 'Technologies',
            entries: [
              { key: 'Technologies Used', value: this.truncateArray(details.technology_names, 10), expandable: true },
              { key: 'Keywords', value: this.truncateArray(details.keywords, 10), expandable: true }
            ]
          }
        ];
      },
      error: (err) => console.error('Error fetching company details:', err)
    });
  }

  /** Utility Methods **/
  toggleField(label: string): void {
    this.expandedFields[label] = !this.expandedFields[label];
  }

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

  truncateArray(arr: string[] | null | undefined, maxItems: number = 100): string {
    if (!arr || arr.length === 0) return 'N/A';
    if (arr.length > maxItems) {
      const visible = arr.slice(0, maxItems).join(', ');
      return `${visible}, ... (+${arr.length - maxItems} more)`;
    }
    return arr.join(', ');
  }

  formatNumber(value: any): string {
    if (value == null) return 'N/A';
    return Number(value).toLocaleString();
  }

  getSentEmails(company_id: number) {
    console.log("Fetching emails...")
    return this.companiesService.viewSentEmails(company_id);
  }

}
