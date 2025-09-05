// company-details.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';
import { CompanyService, CompanySection } from '../../../services/company-details.service';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-company-details',
  standalone: true,
  imports: [CommonModule, MatCardModule],
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
    const id = Number(this.route.snapshot.paramMap.get('id'));

   this.companyService.getCompanyDetails(id).subscribe({
    next: (res) => {
      this.companySections = res; // Already organized into sections
    },
    error: (err) => console.error('Error loading company', err)
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
