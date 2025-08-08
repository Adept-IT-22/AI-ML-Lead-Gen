import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'app-lead-filters',
  standalone: true,
  imports: [],
  templateUrl: './leads-filter.component.html',
  styleUrls: ['./leads-filter.component.css']
})
export class LeadFiltersComponent {

 activeFilters: { [key: string]: string } = {};

onFilterChange(key: string, value: string) {
  this.activeFilters[key] = value;
  console.log('Current Filters:', this.activeFilters);

  // TODO: pass activeFilters to LeadsTableComponent for filtering
}
  clearFilters() {
    this.activeFilters = {};
    console.log('Filters cleared');
  }
}
