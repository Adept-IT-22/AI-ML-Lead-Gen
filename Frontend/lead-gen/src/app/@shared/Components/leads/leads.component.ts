import { Component, Input } from '@angular/core';

import { CommonModule, NgFor } from '@angular/common';



export interface Lead {
  id: number;
  companyName: string;
  status: string;
  dateUpdated: string; // or Date
  score: number;
  source: string;
  industry: string;
}



@Component({

  
  selector: 'app-leads',
  imports:[CommonModule],
  templateUrl: './leads.component.html',
  styleUrls: ['./leads.component.scss']
})
export class LeadsTableComponent {

  



  @Input()leads: Lead[] = [
    {
      id: 1,
      companyName: 'Acme Corp',
      status: 'MQL',
      dateUpdated: '2025-07-21',
      source: 'Google News',
      industry: 'Fintech',
      score: 85,
    },
    {
      id: 2,
      companyName: 'Innovate Inc',
      status: 'SQL',
      dateUpdated: '2025-07-17',
      source: 'Tech.Eu',
      industry: 'Education',
      score: 70,
    },
    {
      id: 3,
      companyName: 'NextGen Ltd',
      status: 'MQL',
      dateUpdated: '2025-07-19',
      source: 'Email Campaign',
      industry: 'AI',
      score: 90,
    },
    {
      id: 4,
      companyName: 'OldCorp',
      status: 'Disqualified',
      dateUpdated: '2025-07-10',
      source: 'Email Blast',
      industry: 'Retail',
      score: 50,
    },
  ];
  
  filteredLeads: Lead[] = [...this.leads];
  @Input() currentFilter: string = '';
  @Input() searchTerm: string = '';

  onSearch(term: string) {
    this.searchTerm = term.toLowerCase();
    this.applyFilters();
  }

  setFilter(filter: string) {
    this.currentFilter = filter;
    this.applyFilters();
  }

  applyFilters() {
    let leads = this.leads;

    if (this.searchTerm) {
      leads = leads.filter(lead =>
        lead.companyName.toLowerCase().includes(this.searchTerm) ||
        lead.status.toLowerCase().includes(this.searchTerm) ||
        lead.source.toLowerCase().includes(this.searchTerm) ||
        lead.industry.toLowerCase().includes(this.searchTerm)||
        lead.score?.toString().includes(this.searchTerm)
      );
    }

    if (this.currentFilter === 'source') {
      leads = leads.filter(lead =>
        lead.source.toLowerCase().includes('google') || lead.source.toLowerCase().includes('email')
      );
    } else if (this.currentFilter === 'status') {
      leads = leads.filter(lead => lead.status.toLowerCase() === 'mql');
    } else if (this.currentFilter === 'date') {
      leads = leads.filter(lead => lead.dateUpdated >= '2025-07-18');
    }else if (this.currentFilter === 'score'){
      leads = leads.filter(lead =>lead.score)
    }

    this.filteredLeads = leads;
  }
 

}

