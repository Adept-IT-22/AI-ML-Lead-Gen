import { Component, AfterViewInit } from '@angular/core';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-engagement',
  templateUrl: './engagement.component.html',
  styleUrls: ['./engagement.component.scss']
})
export class EngagementComponent implements AfterViewInit {

  ngAfterViewInit(): void {
    this.renderFunnel();
    this.renderBreakdown();
    this.renderActivity();
  }

  private renderFunnel() {
    const ctx = document.getElementById('funnelChart') as HTMLCanvasElement;
    if (!ctx) return;

    new Chart(ctx, {
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
        plugins: { legend: { display: false, labels: { color: 'yellow' } }  },
        scales: {
      x: { ticks: { color: 'white' }, grid: { color: 'rgba(233,31,31,0.1)' } },
      y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
      }
    });
  }

 private renderBreakdown() {
  const ctx = document.getElementById('breakdownChart') as HTMLCanvasElement;
  if (!ctx) return;

  new Chart(ctx, {
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
        legend: {
          position: 'bottom',
          labels: { color: 'yellow' }
        }
      }
      // ❌ Removed scales (not needed for doughnut)
    }
  });
}


  private renderActivity() {
    const ctx = document.getElementById('activityChart') as HTMLCanvasElement;
    if (!ctx) return;

    new Chart(ctx, {
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
        plugins: { legend: { display: false , labels: { color: 'yellow' }} }, 
        scales: {
      x: { ticks: { color: 'white' }, grid: { color: 'rgba(233,31,31,0.1)' } },
      y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
      }
    });
  }
}
