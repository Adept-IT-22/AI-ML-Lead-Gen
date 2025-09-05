import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
// backend.service.ts
@Injectable({
  providedIn: 'root'
})
export class BackendService {
  private apiUrl = 'http://localhost:5000'; // Flask backend URL

  constructor(private http: HttpClient) {}

  getCompanyById(id: number): Observable<any> {
  return this.http.get<any>(`${this.apiUrl}/fetch-company/${id}`);
}

  // Trigger pipeline
  runPipeline(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/run`);
  }

  // Fetch companies
  fetchCompanies(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/fetch-companies`);
  }

  // Fetch people
  fetchPeople(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/fetch-people`);
  }
}

