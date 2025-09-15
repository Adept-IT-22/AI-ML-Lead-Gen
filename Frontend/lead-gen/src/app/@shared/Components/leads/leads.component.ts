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
  @Input() data: any[] = [];          // original dataset
  @Input() buttons: string[] = [];
  @Input() selectTitle: string = "";
  @Input() selectOptions: string[] = [];
  @Input() filters: { [key: string]: string } = {}; // active filters
  @Input() fullTable: boolean = false; // default = preview mode

  filteredData: any[] = [];   // ✅ holds filtered + searched results
  selectedOption: string = '';
  selectedRow: any = null;
  searchTerm: string = '';

  constructor(
    private companiesService: CompaniesService, 
    private searchService: SearchService
  ) {}

  ngOnInit(): void {
    this.filteredData = [...this.data]; // start with all data

    // ✅ subscribe to global search term (from Navbar search bar)
    this.searchService.searchTerm$.subscribe(term => {
      this.searchTerm = term.toLowerCase();
      this.applyFiltersAndSearch();
    });
  }

  ngOnChanges():void {
    this.filteredData = [...this.data];
    this.applyFiltersAndSearch();
  }

  /** Called when a filter dropdown changes */
  onSelect(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOption = selectElement.value;
    console.log('Selected:', this.selectedOption);
  }

  /** Called by <app-filter> when filter changes */
  onFilterChange(filter: { key: string, value: string }) {
    this.filters[filter.key] = filter.value;
    this.applyFiltersAndSearch();
  }

  /** Apply both filters + search together */
  applyFiltersAndSearch() {
    this.filteredData = this.data.filter(row => {
      // ✅ Apply filters (all must match)
      const matchesFilters = Object.keys(this.filters).every(key => {
        return !this.filters[key] || row[key] === this.filters[key];
      });

      // ✅ Apply search (any field contains the term)
      const matchesSearch = !this.searchTerm ||
        Object.values(row).some(val =>
          val?.toString().toLowerCase().includes(this.searchTerm)
        );

      return matchesFilters && matchesSearch;
    });
  }

  /** Row actions */
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
