import { Component, Input, OnInit } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';
import { ButtonComponent } from '../button/button.component';
import { RouterModule } from '@angular/router'; 
import { CompaniesService } from '../../Services/companies.service';
import { ICompany } from '../../../Libs/interfaces/company.interface';
import { SearchService } from '../../Services/search.service';
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
  @Input() fullTable: boolean = false; // default = preview mode
  selectedOption: string = '';
  selectedRow: any = null; 

  constructor(private companiesService:CompaniesService, private searchService: SearchService){}
  

  ngOnInit(): void {
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

