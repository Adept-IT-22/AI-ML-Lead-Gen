// company-details.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';
import { CompanyService, CompanySection } from '../../../services/company-details.service';
import { ButtonComponent } from '../button/button.component';
import { DataCardComponent } from '../data-card/data-card.component';

@Component({
  selector: 'app-company-details',
  standalone: true,
  imports: [CommonModule, MatCardModule, ButtonComponent],
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {
  companySections: CompanySection[] | null = null;

  constructor(
    private route: ActivatedRoute,
    private companyService: CompanyService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const companyId = params.get('id'); // <-- comes from /company/:id
      console.log('Incoming companyId:', companyId);

      if (companyId) {
        this.companySections = this.companyService.getCompanyDetails(companyId);
        console.log('Fetched details:', this.companySections);
      }
    });
  }

  isLink(value: string): boolean {
  return value.startsWith('http') || value.includes('www.');
}

formatUrl(value: string): string {
  if (!/^https?:\/\//i.test(value)) {
    return 'https://' + value;
  }
  return value;
}

isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
}
