import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';
import { ButtonComponent } from '../button/button.component';
import { RouterModule } from '@angular/router';
import { CompaniesService } from '../../Services/companies.service';
import { SearchService } from '../../Services/search.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';


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
  activeActionRow: number | null = null;

  //Reference to hidden file input
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  constructor(
    private companiesService: CompaniesService,
    private searchService: SearchService,
    private http: HttpClient
  ) { }

  backend_url = environment.API_URL;

  ngOnInit(): void {
    this.filteredData = [...this.data];
    this.searchService.searchTerm$.subscribe(term => {
      this.searchTerm = term.toLowerCase();
      this.applyFiltersAndSearch();
    });
  }

  ngOnChanges(): void {
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

  hasEmail(row: any): boolean {
    if (typeof row.email === 'string' && row.email.trim().length > 0) {
      return true;
    }
    const people = row.people ?? [];
    return people.some((p: any) =>
      typeof p.email === 'string' && p.email.trim().length > 0
    );
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

  importLeads(): void {
    //Open file selector
    this.fileInput.nativeElement.click();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    //Send to backend
    this.http.post(`${this.backend_url}/import-leads`, formData).subscribe({
      next: (res: any) => {
        console.log('File uploaded successfuly', res);
        alert(res.message || 'File uploaded successfully!');
      },
      error: (err) => {
        console.error('Uploaded failed', err);
        alert('Failed to upload file');
      }
    });

    //Reset filename to empty so that user can select the same file again
    input.value = '';
  }

  // ✅ Toggle Replied status
  toggleReplied(row: any) {
    const newStatus = row.contacted_status !== 'replied';
    this.companiesService.markReplied(row.id, newStatus).subscribe({
      next: () => {
        row.contacted_status = newStatus ? 'replied' : 'engaged';
        console.log('Replied status updated');
      },
      error: (err) => console.error('Failed to update replied status', err)
    });
  }

  // ✅ Toggle Positive Response
  togglePositive(row: any) {
    const newPositive = !row.positive_reply;
    this.companiesService.markPositive(row.id, newPositive).subscribe({
      next: () => {
        row.positive_reply = newPositive;
        if (newPositive) {
          row.contacted_status = 'replied';
        }
        console.log('Positive reply status updated');
      },
      error: (err) => console.error('Failed to update positive status', err)
    });
  }

  // ✅ Toggle Action Menu
  toggleActionMenu(index: number) {
    this.activeActionRow = this.activeActionRow === index ? null : index;
  }
}
