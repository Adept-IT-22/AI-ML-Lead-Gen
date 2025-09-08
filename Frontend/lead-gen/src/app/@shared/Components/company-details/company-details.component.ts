import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CompaniesService, CompanySection } from '../../Services/companies.service';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card'; 

@Component({
  selector: 'app-company-details',
  imports: [CommonModule, MatCardModule],
  standalone: true,
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {
  companyId!: number;
  companyDetails: CompanySection[] | null = null;

  expandedFields: { [key: string]: boolean } = {};

  constructor(private route: ActivatedRoute, private companiesService: CompaniesService) {}

  ngOnInit(): void {
    this.companyId = Number(this.route.snapshot.paramMap.get('id'));

    this.companiesService.getCompanyDetails(this.companyId).subscribe({
      next: (details) => {
        this.companyDetails = details;
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
