import { Component } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { SearchBarComponent } from '../../@shared/Components/search-bar/search-bar.component';
import { DataFeedComponent } from "../../@shared/Components/data-feed/data-feed.component";
import { LeadsTableComponent, TableColumn } from '../../@shared/Components/leads/leads.component';
import { FilterComponent } from '../../@shared/Components/filter/filter.component';
import { NgFor } from '@angular/common';
import { leadData } from '../../Libs/data/lead.data';
import { ILead } from '../../Libs/interfaces/lead.interface';

@Component({
  selector: 'app-home',
  imports: [SearchBarComponent, DataCardComponent, DataFeedComponent, FilterComponent, NgFor, LeadsTableComponent],
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

  news_feed = [
    '[2025-07-21] Acme Corp raises $10M Series A',
    '[2025-07-21] Tech Inc looking for AI Engineer',
    '[2025-07-21] New ML event in Cambridge, MA'
  ];

  activity_feed = [
    '[2025-07-21] Lead 01 status changed to MQL',
    '[2025-07-21] New Lead 02 from Google News',
    '[2025-07-21] Meeting shcedule for lead 03'
  ];

  filters = [
    { optionType: 'BY DATE' },
    { optionType: 'BY SCORE' },
    { optionType: 'BY STATUS' },
    { optionType: 'BY SOURCE' }
  ];

  leadTableColumns: TableColumn[] = [
    {header: 'No'},
    {header: 'Company Name'}
  ]
  
  leadTableData = leadData
}
