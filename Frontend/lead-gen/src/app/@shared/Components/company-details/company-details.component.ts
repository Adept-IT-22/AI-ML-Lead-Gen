//company-details.component.ts
import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
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
  @Input() companyId: string = '';
  companySections: CompanySection[] | null = null;

  constructor(private companyService: CompanyService) {}

  ngOnInit(): void {
    if (this.companyId) {
      this.companySections = this.companyService.getCompanyDetails(this.companyId);
    }
  }
}
