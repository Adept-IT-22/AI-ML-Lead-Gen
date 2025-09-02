import { Component, Input } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';
import { ButtonComponent } from '../button/button.component';
import { RouterModule } from '@angular/router'; 
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

export class LeadsTableComponent {
  @Input()title: string = "";
  @Input()columns: Column[] = [];
  @Input()data: any[] = [];
  @Input() buttons: string[] = [];
  @Input() selectTitle: string = "";
  @Input() selectOptions: string[] = [];
  @Input() filters: { [key: string]: string } = {};
  selectedOption: string = '';
  selectedRow: any = null; 

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

