import { Component, Input } from '@angular/core';
import { NgStyle } from '@angular/common';
import { MatIconModule } from '@angular/material/icon'

@Component({
  selector: 'app-data-card',
  imports: [NgStyle, MatIconModule],
  templateUrl: './data-card.component.html',
  styleUrl: './data-card.component.scss'
})
export class DataCardComponent {
  @Input() title: string = '';
  @Input() data: string = '';
  @Input() progressBar: [] = [];
  @Input() color: string = '';
}
