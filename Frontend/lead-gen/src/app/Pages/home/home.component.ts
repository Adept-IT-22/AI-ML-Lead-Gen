// home.component.ts
import { Component } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { DataFeedComponent } from "../../@shared/Components/data-feed/data-feed.component";
import { LeadsTableComponent } from '../../@shared/Components/leads/leads.component';
import { FilterComponent } from '../../@shared/Components/filter/filter.component';
import { NgFor } from '@angular/common';
import { ButtonComponent } from "../../@shared/Components/button/button.component";

@Component({
  selector: 'app-home',
  imports: [DataCardComponent, DataFeedComponent, FilterComponent, NgFor, LeadsTableComponent],
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
  { optionType: 'BY DATE', options: ['Today', 'This Week', 'This Month'], key: 'date' },
  { optionType: 'BY SCORE', options: ['>80', '<80'], key: 'score' },
  { optionType: 'BY STATUS', options: ['MQL', 'SQL'], key: 'status' },
  { optionType: 'BY SOURCE', options: ['Google News', 'Tech.Eu', 'HackerNews', 'finSMES', 'crunchbase'], key: 'source' }
];

   leadData = [
    { no: '01', companyName: 'Mbodi AI', status: 'MQL', dateUpdated: '2025-07-20', score: '85', source: 'Google News', industry: 'Robotics'},
    { no: '02', companyName: 'Innovate Inc', status: 'SQL', dateUpdated: '2025-07-23', score: '70', source: 'Tech.Eu', industry: 'Education'},
    { no: '03', companyName: 'Tech AI', status: 'MQL', dateUpdated: '2025-07-19', score: '81', source: 'HackerNews', industry: 'Defense'},
    { no: '04', companyName: 'Terraform', status: 'MQL', dateUpdated: '2025-08-08', score: '93', source: 'FinSMES', industry: 'Commerce'},
    { no: '05', companyName: 'AI Ventures', status: 'SQL', dateUpdated: '2025-08-02', score: '78', source: 'Crunchbase', industry: 'Education'},
    { no: '07', companyName: 'Tech AI', status: 'MQL', dateUpdated: '2025-08-01', score: '56', source: 'HackerNews', industry: 'Defense'},
  ];

  // Define the columns for the lead data table
  leadColumns = [
    { key: 'no', header: 'No.' },
    { key: 'companyName', header: 'Company Name' },
    { key: 'status', header: 'Status' },
    { key: 'dateUpdated', header: 'Date Updated' },
    { key: 'score', header: 'Score' },
    { key: 'source', header: 'Source' },
    { key: 'industry', header: 'Industry' },
    { key: 'action', header: 'Action' },
  ];

  buttons: string[] = ['View', 'Update'];
// logic for filters
  filtersState: { [key: string]: string } = {};
  filteredLeads = [...this.leadData];

  onFilterChange(filter: { key: string, value: string }) {
    this.filtersState[filter.key] = filter.value;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredLeads = this.leadData.filter(lead => {
      return Object.entries(this.filtersState).every(([key, value]) => {
        if (!value) return true;
        if (key === 'score') {
          return value === '>80' ? Number(lead.score) > 80 : Number(lead.score) < 80;
        }
        return lead[key as keyof typeof lead] === value;
      });
    });
  }
}
