// company-details.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-company-details',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './company-details.component.html',
  styleUrls: ['./company-details.component.scss']
})
export class CompanyDetailsComponent implements OnInit {

  constructor(
    private route: ActivatedRoute,
  ) {}
  

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));


  }

  isLink(value: string): boolean {
    return value.startsWith('http') || value.includes('www.');
  }

  formatUrl(value: string): string {
    if (!/^https?:\/\//i.test(value)) {
      return 'https://' + value;
    }
    return value;
  }

  isEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }
}
