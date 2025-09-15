import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SearchService } from '../../Services/search.service';
import { ButtonComponent } from '../button/button.component';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [CommonModule, ButtonComponent, MatInputModule, MatFormFieldModule],
  templateUrl: './search-bar.component.html',
  styleUrls: ['./search-bar.component.scss']
})
export class SearchBarComponent {
  searchText: string = '';

  constructor(private searchService: SearchService) {}

  /** Triggered while typing */
  onSearchChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchText = input.value;
    this.searchService.setSearchTerm(this.searchText.trim());
  }

  /** Triggered when clicking GO button */
  onSearch(): void {
    this.searchService.setSearchTerm(this.searchText.trim());
  }
}
