import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { IEvent } from '../../Libs/interfaces/event.interface';
import { environment } from '../../../environments/environment.prod';

@Injectable({
  providedIn: 'root'
})
export class EventService {

  private readonly backend_url = environment.API_URL;

  private http = inject(HttpClient);

  events(): Observable<IEvent[]> {
    console.log("Fetching events from backend...");
    return this.http.get<IEvent[]>(`${this.backend_url}/events`);
  }
}
