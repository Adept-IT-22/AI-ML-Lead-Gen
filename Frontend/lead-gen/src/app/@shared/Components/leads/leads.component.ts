import { Component, Input } from '@angular/core';
import { CommonModule, NgFor } from '@angular/common';

export interface TableColumn {
  header: string;
}

@Component({
  selector: 'app-leads',
  imports:[CommonModule],
  templateUrl: './leads.component.html',
  styleUrls: ['./leads.component.scss']
})
export class LeadsTableComponent {
  @Input() title: string= "";
  @Input() columns: TableColumn[] = [];
  @Input() data: any[] = []
}