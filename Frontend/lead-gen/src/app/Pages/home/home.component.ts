import { Component } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { SearchBarComponent } from '../../@shared/Components/search-bar/search-bar.component';
import { NgFor } from '@angular/common';

@Component({
  selector: 'app-home',
  imports: [SearchBarComponent, DataCardComponent, NgFor],
  standalone: true,
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  stats = [
  { data: '1280', title: 'TOTAL LEADS', color: '#1fedc3'},
  { data: '472', title: 'MQLs', color: '#edce1f'},
  { data: '316', title: 'SQLs', color: '#1fafed' },
  { data: '102', title: 'EMAILS', color: '#1fe4c3' },
  { data: '44', title: 'CONVERSIONS', color: '#1fe41f' },
  { data: '11', title: 'DISQUALIFIED', color: '#e41f1f' }
];

}
