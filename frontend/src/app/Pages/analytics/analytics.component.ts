import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common'; // Moved to top
import { Chart, registerables } from 'chart.js';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { NgChartsModule } from 'ng2-charts';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  standalone: true,
  imports: [CommonModule, NgChartsModule],
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss']
})
export class AnalyticsComponent implements OnInit, OnDestroy {

  private companiesService = inject(CompaniesService);
  public metrics: any = null;
  private charts: Chart[] = [];

  ngOnInit(): void {
    this.loadMetrics();
  }

  ngOnDestroy(): void {
    this.charts.forEach(chart => chart.destroy());
    this.charts = [];
  }

  loadMetrics() {
    this.companiesService.fetchEngagementMetrics().subscribe({
      next: (data) => {
        this.metrics = data;
        // Small delay to ensure DOM is ready for charts
        setTimeout(() => this.renderAllCharts(), 100);
      },
      error: (err) => console.error('Failed to load metrics', err)
    });
  }

  private renderAllCharts() {
    // Destroy existing charts to prevent memory leaks/re-rendering issues
    this.charts.forEach(chart => chart.destroy());
    this.charts = [];

    this.renderFunnel();
    this.renderBreakdown();
    this.renderServiceTraction();
    this.renderICPDistribution();
    this.renderSizeMetrics();
  }

  private renderFunnel() {
    const ctx = document.getElementById('funnelChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.lifecycle) return;

    const data = this.metrics.lifecycle;
    const labels = ['uncontacted', 'contacted', 'opened', 'engaged', 'replied'];
    const values = labels.map(l => data[l] || 0);

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.map(l => l.toUpperCase()),
        datasets: [{
          label: 'Leads',
          data: values,
          backgroundColor: [
            '#64748b', // UNCONTACTED
            '#3b82f6', // CONTACTED
            '#a855f7', // OPENED
            '#22c55e', // ENGAGED
            '#facc15'  // REPLIED
          ]
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { 
          legend: { display: false },
          title: { display: false }
        },
        scales: {
          x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
          y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
        }
      }
    });
    this.charts.push(chart);
  }

  private renderBreakdown() {
    const ctx = document.getElementById('breakdownChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.outreach_kpis) return;

    const kpis = this.metrics.outreach_kpis;
    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Opened', 'Clicked', 'Replied'],
        datasets: [{
          data: [kpis.opened || 0, kpis.clicked || 0, kpis.replied || 0],
          backgroundColor: ['#3b82f6', '#22c55e', '#facc15']
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom', labels: { color: 'yellow' } }
        }
      }
    });
    this.charts.push(chart);
  }

  private renderServiceTraction() {
    const ctx = document.getElementById('serviceTractionChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.service_traction) return;

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.metrics.service_traction.map((s: any) => s.service),
        datasets: [
          {
            label: 'Total Leads',
            data: this.metrics.service_traction.map((s: any) => s.count),
            backgroundColor: 'rgba(59, 130, 246, 0.5)'
          },
          {
            label: 'Replies',
            data: this.metrics.service_traction.map((s: any) => s.replies),
            backgroundColor: '#facc15'
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: 'white' } } },
        scales: {
          x: { ticks: { color: 'white' } },
          y: { ticks: { color: 'white' } }
        }
      }
    });
    this.charts.push(chart);
  }

  private renderICPDistribution() {
    const ctx = document.getElementById('icpDistChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.icp_score_distribution) return;

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.metrics.icp_score_distribution.map((s: any) => `Score ${s.score}`),
        datasets: [{
          label: 'Number of Companies',
          data: this.metrics.icp_score_distribution.map((s: any) => s.count),
          backgroundColor: [
            'rgba(239, 68, 68, 0.8)',  // Score 1
            'rgba(249, 115, 22, 0.8)', // Score 2
            'rgba(234, 179, 8, 0.8)',  // Score 3
            'rgba(34, 197, 94, 0.8)',  // Score 4
            'rgba(59, 130, 246, 0.8)'  // Score 5
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: { 
          legend: { display: false } 
        },
        scales: {
          x: { 
            ticks: { color: 'white' },
            grid: { display: false }
          },
          y: { 
            beginAtZero: true,
            ticks: { color: 'white' },
            grid: { color: 'rgba(255,255,255,0.1)' }
          }
        }
      }
    });
    this.charts.push(chart);
  }

  private renderSizeMetrics() {
    const ctx = document.getElementById('sizeMetricsChart') as HTMLCanvasElement;
    if (!ctx || !this.metrics?.size_metrics) return;

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.metrics.size_metrics.map((s: any) => s.size_range),
        datasets: [{
          label: 'Response Rate (%)',
          data: this.metrics.size_metrics.map((s: any) => (s.replies / s.total) * 100),
          borderColor: '#facc15',
          tension: 0.4,
          fill: false
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: 'white' } },
          y: { 
            ticks: { color: 'white' },
            beginAtZero: true,
            max: 100
          }
        }
      }
    });
    this.charts.push(chart);
  }
}
