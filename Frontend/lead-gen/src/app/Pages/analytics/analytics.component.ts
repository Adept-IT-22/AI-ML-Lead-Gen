import { Component } from '@angular/core';
import { ChartData, ChartOptions } from 'chart.js';
import { NgChartsModule } from 'ng2-charts';

@Component({
  standalone: true,
  imports: [NgChartsModule],
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss']
})
export class AnalyticsComponent {

  // Common options for bar/line charts
  private axisOptions: ChartOptions<'bar' | 'line'> = {
    responsive: true,
    plugins: { 
      legend: { 
        labels: { color: 'white' } // legend text color
      } 
    },
    scales: { 
      x: {
        ticks: { color: 'white' }, // X axis labels
        grid: { color: 'yellow' } // grid lines
      },
      y: {
        beginAtZero: true,
        ticks: { color: 'white' }, // Y axis labels
        grid: { color: 'rgba(255,255,255,0.1)' }
      }
    }
  };

  // 📊 Conversion Funnel
  funnelData: ChartData<'bar'> = {
    labels: ['Total Leads', 'MQLs', 'SQLs', 'Opportunities', 'Conversions'],
    datasets: [
      {
        label: 'Funnel',
        data: [49, 0, 0, 0, 0],
        backgroundColor: ['#00FFFF', '#FFD700', '#00BFFF', '#32CD32', '#FF4500']
      }
    ]
  };
  funnelOptions: ChartOptions<'bar'> = this.axisOptions;

  // 🥧 Leads by Source
  sourceData: ChartData<'pie'> = {
    labels: ['Funding', 'Google News', 'Tech.eu', 'HackerNews'],
    datasets: [
      { 
        data: [20, 10, 12, 7],
        backgroundColor: ['#FFD700', '#00FFFF', '#32CD32', '#FF4500']
      }
    ]
  };
  pieOptions: ChartOptions<'pie'> = {
    responsive: true,
    plugins: {
      legend: { labels: { color: 'white' } } // white legend labels
    }
  };

  // 🥧 Leads by Industry
  industryData: ChartData<'pie'> = {
    labels: ['IT Services', 'Education', 'Fintech', 'Defense', 'Commerce'],
    datasets: [
      { 
        data: [15, 8, 12, 5, 9],
        backgroundColor: ['#FF4500', '#FFD700', '#00FFFF', '#32CD32', '#9370DB']
      }
    ]
  };

  // 🥧 Contact Status
  contactData: ChartData<'pie'> = {
    labels: ['Contacted', 'Uncontacted', 'Opened'],
    datasets: [
      { 
        data: [10, 30, 9],
        backgroundColor: ['#32CD32', '#FFD700', '#00BFFF']
      }
    ]
  };

  // 📈 Leads Over Time
  leadsTrendData: ChartData<'line'> = {
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [
      { 
        label: 'Leads Created',
        data: [5, 12, 18, 14],
        borderColor: '#00FFFF',
        fill: true,
        backgroundColor: 'rgba(0,255,255,0.2)'
      }
    ]
  };
  lineOptions: ChartOptions<'line'> = this.axisOptions;

  // 📊 ICP Score Distribution
  scoreData: ChartData<'bar'> = {
    labels: ['0-40', '41-60', '61-80', '81-100'],
    datasets: [
      {
        label: 'ICP Score',
        data: [5, 15, 20, 9],
        backgroundColor: '#aa29d1ff'
      }
    ]
  };
  barOptions: ChartOptions<'bar'> = this.axisOptions;

  // 🔥 Engagement Heatmap (simulated with bar chart per day)
  engagementData: ChartData<'bar'> = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
    datasets: [
      {
        label: 'Engagement',
        data: [12, 9, 15, 7, 20],
        backgroundColor: '#32CD32'
      }
    ]
  };
  engagementOptions: ChartOptions<'bar'> = this.axisOptions;

}
