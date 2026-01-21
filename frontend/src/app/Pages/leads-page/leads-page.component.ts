import { Component, OnInit } from '@angular/core';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { ICompany } from '../../Libs/interfaces/company.interface';
import { LeadsTableComponent } from '../../@shared/Components/leads/leads.component';
import { NavbarComponent } from '../../@shared/Components/navbar/navbar.component';

@Component({
  standalone: true,
  imports: [LeadsTableComponent],
  selector: 'app-leads-page',
  templateUrl: './leads-page.component.html',
  styleUrls: ['./leads-page.component.scss']
})
export class LeadsPageComponent implements OnInit {
  title = 'Lead List';
  columns = [
    { header: 'Company Name', key: 'name' },
    { header: 'Status', key: 'status' },
    { header: 'Date Updated', key: 'updated_at' },
    { header: 'ICP Score', key: 'icp_score' },
    { header: 'Source', key: 'company_data_source' },
    { header: 'Industry', key: 'industries' },
    { header: 'Action', key: 'action' },
    { header: 'Contact Status', key: 'contacted_status' }
  ];
  data: ICompany[] = [];

  constructor(private companiesService: CompaniesService) {}

  ngOnInit(): void {
    this.companiesService.fetch_companies().subscribe((companies) => {
      this.data = companies;
    });
  }
}
