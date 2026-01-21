import { Component, Input } from '@angular/core';
import { CommonModule, NgStyle } from '@angular/common';
import { MatIconModule } from '@angular/material/icon'

@Component({
  selector: 'app-data-card',
  imports: [NgStyle, MatIconModule, CommonModule],
  templateUrl: './data-card.component.html',
  styleUrl: './data-card.component.scss'
})
export class DataCardComponent {
  @Input() title: string = '';
  @Input() data: string = '';
  @Input() progress: number = 0;
  @Input() color: string = '';


   get progressColor(): string {
    if (this.progress > 0) return '#1fe41f'; // green
    if (this.progress < 0) return '#e41f1f'; // red
    return 'green'; // neutral gray
  }
}
