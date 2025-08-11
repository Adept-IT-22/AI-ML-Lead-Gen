//filter.component.ts
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-filter',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './filter.component.html',
  styleUrl: './filter.component.scss'
})
export class FilterComponent {
   @Input() title: string = "";
  @Input() options: string[] = [];
  @Input() filterKey: string = ""; // key to identify which column this filter applies to

  @Output() filterChanged = new EventEmitter<{ key: string, value: string }>();

  selectedOption: string = '';

  onSelect(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOption = selectElement.value;
    this.filterChanged.emit({ key: this.filterKey, value: this.selectedOption });
  }
}

