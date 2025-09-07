import { Component, Input, OnInit } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';
import { ButtonComponent } from '../button/button.component';
import { RouterModule } from '@angular/router'; 
import { CompaniesService } from '../../Services/companies.service';
export interface Column {
  key: string;
  header: string;
}

@Component({
  selector: 'app-leads',
  imports: [CommonModule, ButtonComponent, NgFor, RouterModule],
  templateUrl: './leads.component.html',
  styleUrls: ['./leads.component.scss']
})

export class LeadsTableComponent implements OnInit{
  @Input()title: string = "";
  @Input()columns: Column[] = [];
  @Input()data: any[] = [];
  @Input() buttons: string[] = [];
  @Input() selectTitle: string = "";
  @Input() selectOptions: string[] = [];
  @Input() filters: { [key: string]: string } = {};
  selectedOption: string = '';
  selectedRow: any = null; 

  constructor(private companiesService:CompaniesService){}

  ngOnInit(): void {
      this.fetchCompanies()
  }

  fetchCompanies(): void{
    this.companiesService.fetch_companies().subscribe({
      next: (companies) => {
        this.data = companies;
      },
      error: (err) => {
        console.error('Error while fetching companies from backend', err)
      }
    })
  }

  onSelect(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOption = selectElement.value;
    console.log('Selected:', this.selectedOption);
  }

  onView(row: any) {
    console.log('Viewing row:', row);
    this.selectedRow = row; // ✅ open modal with row data
  } 

onUpdate(row: any): void {
  console.log('Update clicked', row);
  // handle update logic
}

closeModal() {
    this.selectedRow = null; // ✅ close modal
  }
}

