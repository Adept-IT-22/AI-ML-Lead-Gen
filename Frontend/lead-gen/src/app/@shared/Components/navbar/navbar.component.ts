import { Component, Injectable, Input, OnInit, Output } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";
import { RouterLink } from '@angular/router';
import { EventEmitter } from '@angular/core';
import { SearchService } from '../../Services/search.service';
import { EngagementComponent } from '../../../Pages/engagement/engagement.component';

@Component({
  selector: 'app-navbar',
  imports: [SearchBarComponent, RouterLink],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})

export class NavbarComponent {
   searchText: string = '';

  constructor(private searchService: SearchService) {}

  onSearchChange(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchText = input.value;
    this.searchService.setSearchTerm(this.searchText.trim());
  }
}
