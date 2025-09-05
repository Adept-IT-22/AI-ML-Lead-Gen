import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BackendService } from '../../../services/backend.service';;

@Component({
  selector: 'app-fetch',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './fetch.component.html',
  styleUrls: ['./fetch.component.scss']
})
export class FetchComponent {
  companies: any[] = [];
  people: any[] = [];
  loading = false;
  objectKeys = Object.keys;

  constructor(private backendService: BackendService) {}

  runPipeline() {
    this.loading = true;
    this.backendService.runPipeline().subscribe({
      next: (res) => {
        console.log('Pipeline finished:', res);
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      }
    });
  }

  loadCompanies() {
    this.backendService.fetchCompanies().subscribe({
      next: (res) => this.companies = res,
      error: (err) => console.error(err)
    });
  }

  loadPeople() {
    this.backendService.fetchPeople().subscribe({
      next: (res) => this.people = res,
      error: (err) => console.error(err)
    });
  }

  isArray(value: any): boolean {
    return Array.isArray(value);
  }
}
