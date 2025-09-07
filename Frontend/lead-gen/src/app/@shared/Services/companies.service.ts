import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ICompany } from '../../Libs/interfaces/company.interface';

@Injectable({
  providedIn: 'root'
})
export class CompaniesService {

  private readonly backend_url: string = 'http://127.0.0.1:5000'
  private http = inject(HttpClient)

  fetch_companies(): Observable<ICompany[]> {
    console.log("Fetching company data from backend...")
    return this.http.get<ICompany[]>(`${this.backend_url}/fetch-companies`)
  }
}
