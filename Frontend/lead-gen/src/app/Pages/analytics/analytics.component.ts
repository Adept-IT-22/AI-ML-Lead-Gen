import { Component, OnInit } from '@angular/core';
import { ChartOptions, ChartData } from 'chart.js';
import { NgChartsModule } from 'ng2-charts';
import { CompaniesService } from '../../@shared/Services/companies.service'; // adjust path
import { ICompany } from '../../Libs/interfaces/company.interface';

@Component({
  standalone: true,
  imports: [NgChartsModule],
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss']
})
export class AnalyticsComponent implements OnInit {
  leadsData: ICompany[] = [];

  // ✅ Chart Data
  sourceChartData!: ChartData<'bar'>;
  statusChartData!: ChartData<'pie'>;
  icpChartData!: ChartData<'pie'>;
  timeChartData!: ChartData<'line'>;
  conversionChartData!: ChartData<'bar'>;

  // ✅ Summaries
  sourceSummary = '';
  statusSummary = '';
  icpSummary = '';
  timeSummary = '';
  conversionSummary = '';

  // ✅ Chart Options
  barOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: {
      legend: { labels: { color: 'white' } }
    },
    scales: {
      x: { ticks: { color: 'yellow' }, grid: { color: 'rgba(233,31,31,0.1)' } },
      y: { ticks: { color: 'yellow' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
  };

  pieOptions: ChartOptions<'pie'> = {
    responsive: true,
    plugins: { legend: { labels: { color: 'white' } } }
  };

  lineOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: { legend: { labels: { color: 'white' } } },
    scales: {
      x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
      y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
  };

  constructor(private companiesService: CompaniesService) {}

  ngOnInit() {
    this.loadCompanies();
  }

  private loadCompanies() {
    this.companiesService.fetch_companies().subscribe({
      next: (data) => {
        console.log("Companies fetched: ", data);
        this.leadsData = data;
        this.buildCharts();
      },
      error: (err) => console.error("Error fetching companies", err)
    });
  }

  private buildCharts() {
    // 🔹 Leads by Source → BAR
    const sourceCounts: Record<string, number> = {};
    this.leadsData.forEach(l => {
      sourceCounts[l.company_data_source] = (sourceCounts[l.company_data_source] || 0) + 1;
    });
    this.sourceChartData = {
      labels: Object.keys(sourceCounts),
      datasets: [{
        data: Object.values(sourceCounts),
        backgroundColor: ['#ffcc00', '#33ccff', '#ff6666']
      }]
    };
    this.sourceSummary = `Top source: ${this.getTopKey(sourceCounts)} (${Math.max(...Object.values(sourceCounts))} leads).`;

    // 🔹 Leads by Status → PIE
    const statusCounts: Record<string, number> = {};
    this.leadsData.forEach(l => {
      statusCounts[l.contacted_status] = (statusCounts[l.contacted_status] || 0) + 1;
    });
    this.statusChartData = {
      labels: Object.keys(statusCounts),
      datasets: [{
        data: Object.values(statusCounts),
        backgroundColor: ['#00cc66', '#ff9900', '#cc33ff']
      }]
    };
    this.statusSummary = `Most leads are "${this.getTopKey(statusCounts)}" (${Math.max(...Object.values(statusCounts))}).`;

    // 🔹 ICP Score Buckets → PIE
    const icpBuckets = { '0-25': 0, '25-50': 0, '50-75': 0, '75-100': 0 };
    this.leadsData.forEach(l => {
      const score = parseFloat(l.icp_score as any);
      if (score < 25) icpBuckets['0-25']++;
      else if (score < 50) icpBuckets['25-50']++;
      else if (score < 75) icpBuckets['50-75']++;
      else icpBuckets['75-100']++;
    });
    this.icpChartData = {
      labels: Object.keys(icpBuckets),
      datasets: [{
        data: Object.values(icpBuckets),
        backgroundColor: ['#0099ff', '#33cc33', '#ffcc00', '#ff3333']
      }]
    };
    this.icpSummary = `Most companies fall in the "${this.getTopKey(icpBuckets)}" ICP range.`;

    // 🔹 Leads Over Time → LINE
    const monthCounts: Record<string, number> = {};
    this.leadsData.forEach(l => {
      const date = new Date(l.created_at as any);
      const month = date.toLocaleString('default', { month: 'short', year: 'numeric' });
      monthCounts[month] = (monthCounts[month] || 0) + 1;
    });
    this.timeChartData = {
      labels: Object.keys(monthCounts),
      datasets: [{
        data: Object.values(monthCounts),
        borderColor: '#00ccff',
        backgroundColor: 'rgba(0,204,255,0.3)',
        fill: true
      }]
    };
    this.timeSummary = `Peak leads were in ${this.getTopKey(monthCounts)} (${Math.max(...Object.values(monthCounts))} leads).`;

    // 🔹 Conversion Rate Analysis → BAR
    const totalLeads = this.leadsData.length;
    const mqls = this.leadsData.filter(l => l.status === 'MQL').length;
    const sqls = this.leadsData.filter(l => l.status === 'SQL').length;
    const emailsSent = 22; // TODO: replace with actual email count from service
    const opened = 0;      // TODO: replace with real opened count

    this.conversionChartData = {
      labels: ['Total Leads', 'MQLs', 'SQLs', 'Emails Sent', 'Opened'],
      datasets: [{
        data: [totalLeads, mqls, sqls, emailsSent, opened],
        backgroundColor: ['#00ccff', '#ffcc00', '#33cc33', '#ff9900', '#ff3333']
      }]
    };

    const mqlRate = totalLeads ? ((mqls / totalLeads) * 100).toFixed(1) : '0';
    const sqlRate = mqls ? ((sqls / mqls) * 100).toFixed(1) : '0';
    const openRate = emailsSent ? ((opened / emailsSent) * 100).toFixed(1) : '0';

    this.conversionSummary =
      `MQL Conversion: ${mqlRate}% | SQL Conversion: ${sqlRate}% | Email Open Rate: ${openRate}%`;
  }

  private getTopKey(obj: Record<string, number>): string {
    return Object.entries(obj).reduce((a, b) => (a[1] > b[1] ? a : b))[0];
  }
}
