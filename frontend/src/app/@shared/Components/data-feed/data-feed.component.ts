import { NgFor } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-data-feed',
  standalone: true,
  imports: [NgFor],
  templateUrl: './data-feed.component.html',
  styleUrl: './data-feed.component.scss'
})
export class DataFeedComponent {
  @Input() title: string = '';
  @Input() data: string[] = [];
}