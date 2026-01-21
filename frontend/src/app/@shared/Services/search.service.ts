import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  // Holds the latest search term (default empty string)
  private searchTermSubject = new BehaviorSubject<string>('');
  
  // Observable that components can subscribe to
  searchTerm$ = this.searchTermSubject.asObservable();

  /** Update the search term (called from Navbar or any other component) */
  setSearchTerm(term: string): void {
    this.searchTermSubject.next(term);
  }

  /** Get the current search term without subscribing */
  getSearchTerm(): string {
    return this.searchTermSubject.getValue();
  }
}
