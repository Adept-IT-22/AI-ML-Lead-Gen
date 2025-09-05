import { Component, Injectable, Input, OnInit } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-navbar',
  imports: [SearchBarComponent, RouterLink],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})

export class NavbarComponent implements OnInit {

  ngOnInit(): void {
      
  }

  @Input() menuItems: string[] = [
    "HOME", "ANALYTICS"
  ];

  

}
