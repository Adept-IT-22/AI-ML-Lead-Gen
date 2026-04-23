import { Component, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-engagement',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './engagement.component.html',
  styleUrls: ['./engagement.component.scss']
})
export class EngagementComponent implements AfterViewInit, OnDestroy {
  private charts: Chart[] = [];

  ngAfterViewInit(): void {
    this.renderFunnel();
    this.renderBreakdown();
    this.renderActivity();
  }

  ngOnDestroy(): void {
    this.charts.forEach(chart => chart.destroy());
    this.charts = [];
  }

  private renderFunnel() {
    const ctx = document.getElementById('funnelChart') as HTMLCanvasElement;
    if (!ctx) return;

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Sent', 'Delivered', 'Opened', 'Clicked', 'Replied'],
        datasets: [{
          label: 'Leads',
          data: [220, 200, 100, 50, 12],
          backgroundColor: '#3b82f6'
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
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
    if (!ctx) return;

    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Clicked', 'Replied', 'Unsubscribed'],
        datasets: [{
          data: [50, 12, 8],
          backgroundColor: ['#22c55e', '#facc15', '#ef4444']
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

  private renderActivity() {
    const ctx = document.getElementById('activityChart') as HTMLCanvasElement;
    if (!ctx) return;

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Sept 10', 'Sept 12', 'Sept 14', 'Sept 16', 'Sept 18', 'Sept 20'],
        datasets: [{
          label: 'Engagement',
          data: [2, 4, 8, 6, 9, 12],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }, 
        scales: {
          x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
          y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
        }
      }
    });
    this.charts.push(chart);
  }
}
