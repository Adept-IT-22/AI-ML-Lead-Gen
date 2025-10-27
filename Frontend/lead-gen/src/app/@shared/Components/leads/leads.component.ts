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
  standalone: true,
  imports: [CommonModule, ButtonComponent, NgFor, RouterModule],
  templateUrl: './leads.component.html',
  styleUrls: ['./leads.component.scss']
})
export class LeadsTableComponent implements OnInit {
  @Input() title: string = "";
  @Input() columns: Column[] = [];
  @Input() data: any[] = [];          
  @Input() buttons: string[] = [];
  @Input() selectTitle: string = "";
  @Input() selectOptions: string[] = [];
  @Input() filters: { [key: string]: string } = {}; 
  @Input() fullTable: boolean = false; 

  filteredData: any[] = [];   
  selectedOption: string = '';
  selectedRow: any = null;
  searchTerm: string = '';

  constructor(
    private companiesService: CompaniesService, 
    private searchService: SearchService
  ) {}

  ngOnInit(): void {
    this.filteredData = [...this.data];
    this.searchService.searchTerm$.subscribe(term => {
      this.searchTerm = term.toLowerCase();
      this.applyFiltersAndSearch();
    });
  }

  ngOnChanges():void {
    this.filteredData = [...this.data];
    this.applyFiltersAndSearch();
  }

  onSelect(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOption = selectElement.value;
  }

  onFilterChange(filter: { key: string, value: string }) {
    this.filters[filter.key] = filter.value;
    this.applyFiltersAndSearch();
  }

  applyFiltersAndSearch() {
    this.filteredData = this.data.filter(row => {
      const matchesFilters = Object.keys(this.filters).every(key => {
        return !this.filters[key] || row[key] === this.filters[key];
      });
      const matchesSearch = !this.searchTerm ||
        Object.values(row).some(val =>
          val?.toString().toLowerCase().includes(this.searchTerm)
        );
      return matchesFilters && matchesSearch;
    });
  }

  onView(row: any) {
    this.selectedRow = row;
  } 

  onUpdate(row: any): void {
    console.log('Update clicked', row);
  }

  closeModal() {
    this.selectedRow = null;
  }

  // ✅ Export to Excel
  exportToExcel(): void {
  this.companiesService.exportCompanies().subscribe({
    next: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads-${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    error: (err) => {
      console.error("Export failed:", err);
      alert("Failed to export leads.");
    }
  });
}

importLeads():void {
  
}
}
