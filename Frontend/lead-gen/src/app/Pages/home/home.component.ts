// home.component.ts
import { Component, OnInit } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { DataFeedComponent } from "../../@shared/Components/data-feed/data-feed.component";
import { LeadsTableComponent } from '../../@shared/Components/leads/leads.component';
import { FilterComponent } from '../../@shared/Components/filter/filter.component';
import { NgFor } from '@angular/common';
import { ButtonComponent } from "../../@shared/Components/button/button.component";
import { CompaniesService } from '../../@shared/Services/companies.service';
import { ICompany } from '../../Libs/interfaces/company.interface';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner'
import { NavbarComponent } from '../../@shared/Components/navbar/navbar.component';

@Component({
  selector: 'app-home',
  imports: [DataCardComponent, DataFeedComponent, FilterComponent, NgFor, LeadsTableComponent],
  standalone: true,
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit{
  leadData: ICompany[] = [];
  loading = true;

  constructor(private companiesService: CompaniesService){}

  ngOnInit(): void {
    this.loading = true;
    this.companiesService.fetch_companies().subscribe({
      next: (companies) => {
        //Sort companies by updated_at in descending order i.e. newest 1st
        this.leadData = companies.sort((a, b) => {
          const dateA = new Date(a.updated_at || '').getTime();
          const dateB = new Date(b.updated_at || '').getTime();
          return dateB - dateA;
        });
        this.filteredLeads = companies;
        this.loading = false;
      },
      error: (err) => {
        console.error("Error fetching companies.", err);
        this.loading = false;
      }
    })
  }

  get stats() {
    const total = this.filteredLeads.length;
    const mql = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'mql').length;
    const sql = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'sql').length;
    const emails = this.filteredLeads.filter(lead => lead.contacted_status?.toLowerCase() === 'contacted').length;
    const opened = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'converted').length;
    const disqualified = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'disqualified').length;

    return [
      { data: total.toString(), title: 'TOTAL LEADS', color: '#1fedc3' },
      { data: mql.toString(), title: 'MQLs', color: '#edce1f' },
      { data: sql.toString(), title: 'SQLs', color: '#1fafed' },
      { data: emails.toString(), title: 'EMAILS', color: '#1fe4c3' },
      { data: opened.toString(), title: 'OPENED', color: '#1fe41f' },
      { data: disqualified.toString(), title: 'DISQUALIFIED', color: '#e41f1f' }
    ];
  }

  get weeklyStats() {
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(today.getDate() - 7);
    sevenDaysAgo.setHours(0, 0, 0, 0);

    const leadsThisWeek = this.filteredLeads.filter(lead => {
      if (!lead.updated_at) return false;
      const leadDate = new Date(lead.updated_at);
      return leadDate >= sevenDaysAgo && leadDate <= today;
    });

    const total = leadsThisWeek.length;
    const mql = leadsThisWeek.filter(lead => lead.status?.toLowerCase() === 'mql').length;
    const sql = leadsThisWeek.filter(lead => lead.status?.toLowerCase() === 'sql').length;
    const emails = leadsThisWeek.filter(lead => lead.status?.toLowerCase() === 'emails').length;
    const opened = leadsThisWeek.filter(lead => lead.status?.toLowerCase() === 'converted').length;
    const disqualified = leadsThisWeek.filter(lead => lead.status?.toLowerCase() === 'disqualified').length;

    return [
      { data: total.toString(), title: 'LEADS THIS WEEK', color: '#1fedc3' },
      { data: mql.toString(), title: 'MQLs THIS WEEK', color: '#edce1f' },
      { data: sql.toString(), title: 'SQLs THIS WEEK', color: '#1fafed' },
      { data: emails.toString(), title: 'EMAILS THIS WEEK', color: '#1fe4c3' },
      { data: opened.toString(), title: 'OPENED THIS WEEK', color: '#1fe41f' },
      { data: disqualified.toString(), title: 'DISQUALIFIED THIS WEEK', color: '#e41f1f' }
    ];
  }

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
  { optionType: 'BY DATE', options: ['All', 'Today', 'This Week', 'This Month'], key: 'updated_at' },
  { optionType: 'BY SCORE', options: ['All', '90+', '80-89', '70-79', '60-69', '<60'], key: 'icp_score' },
  { optionType: 'BY CONTACTED STATUS', options: ['All', 'Uncontacted', 'Contacted', 'Pending', 'Requested', 'Engaged', 'Failed', 'Opted Out'], key: 'contacted_status' },
  { optionType: 'BY SOURCE', options: ['All', 'Funding', 'Hiring', 'Events'], key: 'company_data_source' }
];

  // Define the columns for the lead data table
  leadColumns = [
    { key: 'name', header: 'Company Name' },
    { key: 'status', header: 'Status' },
    { key: 'updated_at', header: 'Date Updated' },
    { key: 'icp_score', header: 'ICP Score' },
    { key: 'company_data_source', header: 'Source' },
    { key: 'industries', header: 'Industry' },
    {key: 'contacted_status', header: 'Contact Status'},
    { key: 'action', header: 'Action' },
  ];

  buttons: string[] = ['View', 'Update'];
// logic for filters
  filtersState: { [key: string]: string } = {};
  filteredLeads: ICompany[] = [];

  onFilterChange(filter: { key: string, value: string }) {
    this.filtersState[filter.key] = filter.value;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredLeads = this.leadData.filter(lead => {
      return Object.entries(this.filtersState).every(([key, value]) => {
        if (!value) return true;

        if (value === 'All'){
          delete this.filtersState[key];
        }

        if (key === 'icp_score') {
          const score = Number(lead.icp_score)
          switch (value) {
            case '90+':
              return score >= 90;
            case '80-89':
              return score >= 80 && score <= 89;
            case '70-79':
              return score >= 70 && score <= 79;
            case '60-69':
              return score >= 60 && score <= 69;
            case '<60':
              return score < 60;
            default:
              return true;
          }
        }

        if (key === 'company_data_source') {
          return lead.company_data_source?.toLowerCase() === value.toLowerCase();
        }

        if (key === 'status') {
          return lead.status?.toLowerCase() === value.toLowerCase();
        }

        if (key === 'contacted_status') {
          return lead.contacted_status?.toLowerCase() === value.toLowerCase();
        }

        if (key === 'updated_at') {
          if (!lead.updated_at) return false;
          const leadDate = new Date(lead.updated_at);
          const today = new Date();
          if (value === 'Today') {
          return leadDate.toISOString().slice(0, 10) === today.toISOString().slice(0, 10);
          }
          if (value === 'This Week') {
            const startOfWeek = new Date(today);
            startOfWeek.setDate(today.getDate() - today.getDay());
            startOfWeek.setHours(0, 0, 0, 0);
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);
            endOfWeek.setHours(23, 59, 59, 999);
            return leadDate >= startOfWeek && leadDate <= endOfWeek;
          }
          if (value === 'This Month') {
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59, 999);
            return leadDate >= startOfMonth && leadDate <= endOfMonth;
          }
          return true;
        }

        return lead[key as keyof ICompany] === value;
      });
    });
  }

  get statsWithProgress() {
    // Calculate current stats
    const total = this.filteredLeads.length;
    const mql = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'mql').length;
    const sql = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'sql').length;
    const emails = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'emails').length;
    const opened = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'converted').length;
    const disqualified = this.filteredLeads.filter(lead => lead.status?.toLowerCase() === 'disqualified').length;

    // Calculate last week's stats
    const today = new Date();
    const lastWeekStart = new Date(today);
    lastWeekStart.setDate(today.getDate() - 14);
    lastWeekStart.setHours(0, 0, 0, 0);
    const lastWeekEnd = new Date(today);
    lastWeekEnd.setDate(today.getDate() - 7);
    lastWeekEnd.setHours(23, 59, 59, 999);

    const leadsLastWeek = this.filteredLeads.filter(lead => {
      if (!lead.updated_at) return false;
      const leadDate = new Date(lead.updated_at);
      return leadDate >= lastWeekStart && leadDate <= lastWeekEnd;
    });

    const totalLW = leadsLastWeek.length;
    const mqlLW = leadsLastWeek.filter(lead => lead.status?.toLowerCase() === 'mql').length;
    const sqlLW = leadsLastWeek.filter(lead => lead.status?.toLowerCase() === 'sql').length;
    const emailsLW = leadsLastWeek.filter(lead => lead.status?.toLowerCase() === 'emails').length;
    const openedLW = leadsLastWeek.filter(lead => lead.status?.toLowerCase() === 'converted').length;
    const disqualifiedLW = leadsLastWeek.filter(lead => lead.status?.toLowerCase() === 'disqualified').length;

    // Helper to calculate percent change
    const percentChange = (current: number, previous: number) => {
      if (previous === 0) return current === 0 ? 0 : 100;
      return Math.round(((current - previous) / previous) * 100);
    };

    return [
      { data: total.toString(), title: 'TOTAL LEADS', color: '#1fedc3', progress: percentChange(total, totalLW) },
      { data: mql.toString(), title: 'MQLs', color: '#edce1f', progress: percentChange(mql, mqlLW) },
      { data: sql.toString(), title: 'SQLs', color: '#1fafed', progress: percentChange(sql, sqlLW) },
      { data: emails.toString(), title: 'EMAILS', color: '#1fe4c3', progress: percentChange(emails, emailsLW) },
      { data: opened.toString(), title: 'OPENED', color: '#1fe41f', progress: percentChange(opened, openedLW) },
      { data: disqualified.toString(), title: 'DISQUALIFIED', color: '#e41f1f', progress: percentChange(disqualified, disqualifiedLW) }
    ];
  }
}
