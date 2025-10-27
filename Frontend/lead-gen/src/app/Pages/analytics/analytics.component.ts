// analytics.component.ts
import { Component, OnInit } from '@angular/core';
import { ChartOptions, ChartData } from 'chart.js';
import { NgChartsModule } from 'ng2-charts';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { ICompany } from '../../Libs/interfaces/company.interface';
import { CommonModule } from '@angular/common';
import { count } from 'console';

@Component({
  standalone: true,
  imports: [NgChartsModule, CommonModule],
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss']
})
export class AnalyticsComponent implements OnInit {
  leadsData: ICompany[] = [];

  // ✅ Summary Metrics
  totalLeads = 0;
  conversionRate = 0;
  contactedRate = 0;
  openRate = 0;
  emailsSent = 0;
  opened = 0;

  // ✅ Chart Data
  sourceChartData!: ChartData<'bar'>;
  statusChartData!: ChartData<'pie'>;
  icpChartData!: ChartData<'pie'>;
  timeChartData!: ChartData<'line'>;
  conversionChartData!: ChartData<'bar'>;

  // ✅ Text Summaries
  sourceSummary = '';
  statusSummary = '';
  icpSummary = '';
  timeSummary = '';
  conversionSummary = '';

  isLoading = true;
  hasError = false;

  // 🔹 Event normalization map
  private readonly EVENT_STATUS_MAP: Record<string, { status: string; precedence: number }> = {
    processed: { status: 'pending', precedence: 2 },
    delivered: { status: 'contacted', precedence: 3 },
    open: { status: 'contacted', precedence: 3 },
    click: { status: 'engaged', precedence: 4 },
    bounce: { status: 'failed', precedence: 1 },
    spamreport: { status: 'failed', precedence: 1 },
    unsubscribe: { status: 'opted_out', precedence: 5 },
    dropped: { status: 'failed', precedence: 1 },
    deferred: { status: 'pending', precedence: 2 },
    pending: { status: 'pending', precedence: 2 },
    contacted: { status: 'contacted', precedence: 3 },
    engaged: { status: 'engaged', precedence: 4 },
    failed: { status: 'failed', precedence: 1 },
    opted_out: { status: 'opted_out', precedence: 5 }
  };

  private readonly STATUS_COLORS: Record<string, string> = {
    pending: '#facc15',
    contacted: '#22c55e',
    engaged: '#00ccff',
    failed: '#ef4444',
    opted_out: '#a855f7',
    N_A: '#9ca3af'
  };

  // ✅ Chart.js Options (white labels for dark background)
  barOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: {
      legend: { labels: { color: 'white' } }
    },
    scales: {
      x: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255,255,255,0.05)' },
        title: { display: true, text: 'Categories', color: 'white' }
      },
      y: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255,255,255,0.05)' },
        title: { display: true, text: 'Values', color: 'white' }
      }
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
      x: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255,255,255,0.05)' },
        title: { display: true, text: 'Timeline', color: 'white' }
      },
      y: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255,255,255,0.05)' },
        title: { display: true, text: 'Lead Count', color: 'white' }
      }
    }
  };

  constructor(private companiesService: CompaniesService) {}

  ngOnInit(): void {
    this.loadCompanies();
  }

  /** 🔹 Fetch company data */
  private loadCompanies(): void {
    this.isLoading = true;
    this.hasError = false;

    this.companiesService.fetch_companies().subscribe({
      next: (data) => {
        this.leadsData = data || [];
        this.totalLeads = this.leadsData.length;
        this.calculateSummaryMetrics();
        this.buildCharts();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error fetching companies:', err);
        this.hasError = true;
        this.isLoading = false;
      }
    });
  }

  /** 🔹 Compute Summary Metrics */
  private calculateSummaryMetrics(): void {
    const total = this.leadsData.length || 1;

    // ✅ Get emailSent directly from CompaniesService if available
    this.companiesService.getEmailSentCount().subscribe(emailCount => {
    this.emailsSent = emailCount;
  });


    // Fallback: derive from contact_status
    const emailsSent = this.leadsData.filter(l =>
      (l.contacted_status || '').toLowerCase().includes('contacted')
    ).length;


    const mqls = this.leadsData.filter(l => l.status === 'MQL').length;
    const sqls = this.leadsData.filter(l => l.status === 'SQL').length;

    // ✅ Compute corrected metrics
    this.conversionRate = parseFloat(((sqls / (mqls || 1)) * 100).toFixed(1));
    this.contactedRate = parseFloat(((emailsSent/ (total)) * 100).toFixed(2)); // e.g. 45.05%
    this.openRate = parseFloat(((this.opened / (this.emailsSent || 1)) * 100).toFixed(1));
  }

  /** 🔹 Build all analytics charts */
  private buildCharts(): void {
    if (!this.leadsData.length) return;

    /* ------------------- Leads by Source → BAR ------------------- */
    const sourceCounts: Record<string, number> = {};
    for (const l of this.leadsData) {
      const src = l.company_data_source || 'Unknown';
      sourceCounts[src] = (sourceCounts[src] || 0) + 1;
    }

    this.sourceChartData = {
      labels: Object.keys(sourceCounts),
      datasets: [
        {
          data: Object.values(sourceCounts),
          backgroundColor: ['#facc15', '#22c55e', '#3b82f6', '#ef4444']
        }
      ]
    };
    this.sourceSummary = `Top source: ${this.getTopKey(sourceCounts)} (${Math.max(...Object.values(sourceCounts))} leads).`;

    /* ------------------- Leads by Status → PIE ------------------- */
    const statusCounts: Record<string, number> = {};
    for (const l of this.leadsData) {
      const raw = (l.contacted_status || '').toLowerCase().trim();
      const mapped = this.EVENT_STATUS_MAP[raw];
      const status = mapped ? mapped.status : 'Not-contacted';
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    }

    this.statusChartData = {
      labels: Object.keys(statusCounts),
      datasets: [
        {
          data: Object.values(statusCounts),
          backgroundColor: Object.keys(statusCounts).map(s => this.STATUS_COLORS[s] || '#9ca3af')
        }
      ]
    };
    this.statusSummary = `Most leads are "${this.getTopKey(statusCounts)}".`;

    /* ------------------- ICP Score Distribution → PIE ------------------- */
    const icpBuckets = { '0–25': 0, '25–50': 0, '50–75': 0, '75–100': 0 };
    for (const l of this.leadsData) {
      const score = parseFloat(l.icp_score as any);
      if (!isNaN(score)) {
        if (score < 25) icpBuckets['0–25']++;
        else if (score < 50) icpBuckets['25–50']++;
        else if (score < 75) icpBuckets['50–75']++;
        else icpBuckets['75–100']++;
      }
    }

    this.icpChartData = {
      labels: Object.keys(icpBuckets),
      datasets: [
        {
          data: Object.values(icpBuckets),
          backgroundColor: ['#3b82f6', '#10b981', '#facc15', '#ef4444']
        }
      ]
    };
    this.icpSummary = `Most companies fall in "${this.getTopKey(icpBuckets)}" ICP range.`;

    /* ------------------- Leads Over Time → LINE ------------------- */
    const monthCounts: Record<string, number> = {};
    for (const l of this.leadsData) {
      if (l.created_at) {
        const date = new Date(l.created_at);
        const month = date.toLocaleString('default', { month: 'short', year: 'numeric' });
        monthCounts[month] = (monthCounts[month] || 0) + 1;
      }
    }

    this.timeChartData = {
      labels: Object.keys(monthCounts),
      datasets: [
        {
          data: Object.values(monthCounts),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.3)',
          fill: true,
          tension: 0.4
        }
      ]
    };
    if (Object.keys(monthCounts).length) {
      this.timeSummary = `Peak leads were in ${this.getTopKey(monthCounts)}.`;
    }

    /* ------------------- Conversion Rate → BAR ------------------- */
    const mqls = this.leadsData.filter(l => l.status === 'MQL').length;
    const sqls = this.leadsData.filter(l => l.status === 'SQL').length;

    this.conversionChartData = {
      labels: ['Total Leads', 'MQLs', 'SQLs', 'Emails Sent', 'Opened'],
      datasets: [
        {
          data: [this.totalLeads, mqls, sqls, this.emailsSent, this.opened],
          backgroundColor: ['#3b82f6', '#facc15', '#22c55e', '#f97316', '#ef4444']
        }
      ]
    };

    this.conversionSummary = `MQL Conversion: ${this.conversionRate}% | SQL Conversion: ${((sqls / (mqls || 1)) * 100).toFixed(1)}% | Open Rate: ${this.openRate}%`;
  }

  /** 🔹 Utility: find top key by count */
  private getTopKey(obj: Record<string, number>): string {
    const entries = Object.entries(obj);
    if (!entries.length) return 'N/A';
    return entries.reduce((a, b) => (a[1] > b[1] ? a : b))[0];
  }
}
