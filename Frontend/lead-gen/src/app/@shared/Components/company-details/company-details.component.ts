import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';
import { CompaniesService } from '../../Services/companies.service';
import { ICompany } from '../../../Libs/interfaces/company.interface';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-company-details',
  standalone: true,
  imports: [CommonModule, MatCardModule, ButtonComponent],
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {
  companyDetails: ICompany[] | null = null;
  constructor(
    private route: ActivatedRoute,
    private companiesService: CompaniesService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const companyId = params.get('id'); // <-- comes from /company/:id
      console.log('Incoming companyId:', companyId);

      if (companyId) {
        this.companiesService.getCompanyDetails(Number(companyId)).subscribe({
          next:(companyDetailsData: any) => {
            this.companyDetails = companyDetailsData
          },
          error: (err: any) => {
            console.error(`Error fetching company ID: ${companyId}`, err)
          }
        })
        console.log('Fetched details:', this.companyDetails);
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