import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { IEvent } from '../../Libs/interfaces/event.interface';

@Injectable({
  providedIn: 'root'
})
export class EventService {

  //FOR USE IN DEV
  private readonly backend_url: string = 'http://192.168.1.54:5000';// (For the office)
  //private readonly backend_url: string = 'http://127.0.0.1:5000'; (For at home)

  //FOR USE IN PROD
  //private readonly backend_url: string = '/api';

  private http = inject(HttpClient);

  events(): Observable<IEvent[]> {
    console.log("Fetching events from backend...");
    return this.http.get<IEvent[]>(`${this.backend_url}/events`);
  }
}
