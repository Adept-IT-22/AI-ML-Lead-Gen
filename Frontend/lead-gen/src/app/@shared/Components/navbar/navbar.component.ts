import { Component, Injectable, Input, OnInit, Output } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";
import { RouterLink } from '@angular/router';
import { EventEmitter } from '@angular/core';
import { SearchService } from '../../Services/search.service';

@Component({
  selector: 'app-navbar',
  imports: [SearchBarComponent, RouterLink],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})

export class NavbarComponent {
  @Input() menuItems: string[] = [
    "HOME", "ANALYTICS"
  ];

  constructor(private searchService: SearchService){}

  onSearch(query: string){
    this.searchService.updateQuery(query);
  }

}
