import { Component, OnInit } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { DataFeedComponent } from "../../@shared/Components/data-feed/data-feed.component";
import { LeadsTableComponent } from '../../@shared/Components/leads/leads.component';
import { FilterComponent } from '../../@shared/Components/filter/filter.component';
import { NgFor } from '@angular/common';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { ICompany } from '../../Libs/interfaces/company.interface';
import { NavbarComponent } from '../../@shared/Components/navbar/navbar.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DataCardComponent, DataFeedComponent, FilterComponent, NgFor, LeadsTableComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  leadData: ICompany[] = [];
  filteredLeads: ICompany[] = [];
  loading = true;
  statsVisible: any[] = [];

  constructor(private companiesService: CompaniesService) { }

  ngOnInit(): void {
    this.loading = true;
    this.companiesService.fetch_companies().subscribe({
      next: (companies) => {
        this.leadData = companies.sort((a, b) => {
          const dateA = new Date(a.updated_at || '').getTime();
          const dateB = new Date(b.updated_at || '').getTime();
          return dateB - dateA;
        });
        this.filteredLeads = [...this.leadData];
        this.calculateStats();
        this.loading = false;
      },
      error: (err) => {
        console.error("Error fetching companies.", err);
        this.loading = false;
      }
    });
  }

  /** === SMART STATS WITH WEEKLY PROGRESS === **/
  calculateStats() {
    const total = this.filteredLeads.length;
    const today = new Date();

    // Define date ranges
    const thisWeekStart = new Date(today);
    thisWeekStart.setDate(today.getDate() - 7);
    thisWeekStart.setHours(0, 0, 0, 0);

    const lastWeekStart = new Date(today);
    lastWeekStart.setDate(today.getDate() - 14);
    lastWeekStart.setHours(0, 0, 0, 0);

    const lastWeekEnd = new Date(today);
    lastWeekEnd.setDate(today.getDate() - 7);
    lastWeekEnd.setHours(23, 59, 59, 999);

    // Filter data by time windows
    const leadsThisWeek = this.filteredLeads.filter(lead => {
      if (!lead.updated_at) return false;
      const d = new Date(lead.updated_at);
      return d >= thisWeekStart && d <= today;
    });

    const leadsLastWeek = this.filteredLeads.filter(lead => {
      if (!lead.updated_at) return false;
      const d = new Date(lead.updated_at);
      return d >= lastWeekStart && d <= lastWeekEnd;
    });

    // --- MQLs (ICP ≥ 70) ---
    const totalMQLs = this.filteredLeads.filter(l => Number(l.icp_score) >= 70).length;
    const mqlsThisWeek = leadsThisWeek.filter(l => Number(l.icp_score) >= 70).length;
    const mqlsLastWeek = leadsLastWeek.filter(l => Number(l.icp_score) >= 70).length;

    // --- Counts this week ---
    const countThis = {
      total: leadsThisWeek.length,
      mql: mqlsThisWeek,
      sql: leadsThisWeek.filter(l => l.status?.toLowerCase() === 'sql').length,
      emails: leadsThisWeek.filter(l => l.contacted_status?.toLowerCase() === 'contacted').length,
      opened: leadsThisWeek.filter(l => l.status?.toLowerCase() === 'converted').length,
      disqualified: leadsThisWeek.filter(l => l.status?.toLowerCase() === 'disqualified').length
    };

    // --- Counts last week ---
    const countLast = {
      total: leadsLastWeek.length,
      mql: mqlsLastWeek,
      sql: leadsLastWeek.filter(l => l.status?.toLowerCase() === 'sql').length,
      emails: leadsLastWeek.filter(l => l.contacted_status?.toLowerCase() === 'contacted').length,
      opened: leadsLastWeek.filter(l => l.status?.toLowerCase() === 'converted').length,
      disqualified: leadsLastWeek.filter(l => l.status?.toLowerCase() === 'disqualified').length
    };

    // --- Overall EMAILS ---
    const overallEmails = this.filteredLeads.filter(
      l => l.contacted_status?.toLowerCase() === 'contacted'
    ).length;

    // --- Percent change formula ---
    const percentChange = (thisW: number, lastW: number, totalLeads: number) => {
      if (totalLeads === 0) return 0;
      const diff = thisW - lastW;
      const change = Math.round((diff / totalLeads) * 100);
      return isNaN(change) ? 0 : change;
    };

    this.statsVisible = [
      {
        data: total.toString(),
        title: 'TOTAL LEADS',
        color: '#1fedc3',
        progress: percentChange(countThis.total, countLast.total, total)
      },
      {
        data: totalMQLs.toString(),
        title: 'MQLs',
        color: '#edce1f',
        progress: percentChange(countThis.mql, countLast.mql, total)
      },
      {
        data: countThis.sql.toString(),
        title: 'SQLs',
        color: '#1fafed',
        progress: percentChange(countThis.sql, countLast.sql, total)
      },
      {
        data: overallEmails.toString(),
        title: 'EMAILS',
        color: '#1fe4c3',
        progress: percentChange(countThis.emails, countLast.emails, total)
      },
      {
        data: countThis.opened.toString(),
        title: 'OPENED',
        color: '#1fe41f',
        progress: percentChange(countThis.opened, countLast.opened, total)
      },
      {
        data: countThis.disqualified.toString(),
        title: 'DISQUALIFIED',
        color: '#e41f1f',
        progress: percentChange(countThis.disqualified, countLast.disqualified, total)
      }
    ];
  }

  /** === FILTERS === **/
  filters = [
    { optionType: 'BY DATE', options: ['All', 'Today', 'This Week', 'This Month'], key: 'updated_at' },
    { optionType: 'BY SCORE', options: ['All', '90+', '80-89', '70-79', '60-69', '<60'], key: 'icp_score' },
    { optionType: 'BY CONTACTED STATUS', options: ['All', 'Uncontacted', 'Contacted', 'Pending', 'Requested', 'Engaged', 'Failed', 'Opted Out'], key: 'contacted_status' },
    { optionType: 'BY SOURCE', options: ['All', 'Funding', 'Hiring', 'Events'], key: 'company_data_source' },
    { optionType: 'BY EMAIL FOUND', options: ['All', 'Email Found', 'No Email'], key: 'email_found' }
  ];

  filtersState: { [key: string]: string } = {};

  onFilterChange(filter: { key: string; value: string }) {
    this.filtersState[filter.key] = filter.value;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredLeads = this.leadData.filter(lead =>
      Object.entries(this.filtersState).every(([key, value]) => {
        if (!value || value === 'All') return true;

        if (key === 'icp_score') {
          const score = Number(lead.icp_score);
          switch (value) {
            case '90+': return score >= 90;
            case '80-89': return score >= 80 && score <= 89;
            case '70-79': return score >= 70 && score <= 79;
            case '60-69': return score >= 60 && score <= 69;
            case '<60': return score < 60;
            default: return true;
          }
        }

        if (key === 'company_data_source') return lead.company_data_source?.toLowerCase() === value.toLowerCase();
        if (key === 'status') return lead.status?.toLowerCase() === value.toLowerCase();
        if (key === 'contacted_status') return lead.contacted_status?.toLowerCase() === value.toLowerCase();

        if (key === 'updated_at' && lead.updated_at) {
          const leadDate = new Date(lead.updated_at);
          const today = new Date();

          if (value === 'Today') return leadDate.toDateString() === today.toDateString();
          if (value === 'This Week') {
            const startOfWeek = new Date(today);
            startOfWeek.setDate(today.getDate() - today.getDay());
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);
            return leadDate >= startOfWeek && leadDate <= endOfWeek;
          }
          if (value === 'This Month') {
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            return leadDate >= startOfMonth && leadDate <= endOfMonth;
          }
        }

        if (key === 'email_found') {
          const hasDirectEmail = typeof lead['email'] === 'string' && lead['email'].trim().length > 0;
          const people = lead.people ?? [];

          const hasEmail = hasDirectEmail || people.some(p =>
            typeof p.email === 'string' && p.email.trim().length > 0
          );

          if (value == 'Email Found') return hasEmail;
          if (value == 'No Email') return !hasEmail;
        }

        return true;
      })
    );
    this.calculateStats();
  }

  /** === LEAD TABLE CONFIG === **/
  leadColumns = [
    { key: 'name', header: 'Company Name' },
    { key: 'status', header: 'Status' },
    { key: 'updated_at', header: 'Date Updated' },
    { key: 'icp_score', header: 'ICP Score' },
    { key: 'company_data_source', header: 'Source' },
    { key: 'industries', header: 'Industry' },
    { key: 'service', header: 'Service' },
    { key: 'contacted_status', header: 'Contact Status' },
    { key: 'action', header: 'Action' },
  ];

  buttons: string[] = ['View', 'Update'];

  /** === FEEDS === **/
  news_feed = [
    '[2025-07-21] Acme Corp raises $10M Series A',
    '[2025-07-21] Tech Inc looking for AI Engineer',
    '[2025-07-21] New ML event in Cambridge, MA'
  ];

  activity_feed = [
    '[2025-07-21] Lead 01 status changed to MQL',
    '[2025-07-21] New Lead 02 from Google News',
    '[2025-07-21] Meeting scheduled for Lead 03'
  ];

}
