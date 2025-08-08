import { Component, Input } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';
import { ButtonComponent } from '../button/button.component';

export interface Column {
  key: string;
  header: string;
}

@Component({
  selector: 'app-leads',
  imports: [CommonModule, ButtonComponent],
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
  selectedOption: string = '';

  onSelect(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOption = selectElement.value;
    console.log('Selected:', this.selectedOption);
  }

 onView(row: any) {
  console.log('Viewing row:', row);
  // Perform whatever action you need
} 

onUpdate(row: any): void {
  console.log('Update clicked', row);
  // handle update logic
}
}

