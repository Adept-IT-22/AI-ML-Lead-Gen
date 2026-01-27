import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class UnsubscribeService {
  private apiUrl = environment.API_URL;

  constructor(private http: HttpClient) {}

  unsubscribe(token: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/unsubscribe`, { token });
  }
}
