import { Component, Injectable, Input, OnInit } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";
import { NgFor } from '@angular/common';

@Component({
  selector: 'app-navbar',
  imports: [SearchBarComponent, NgFor],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})

@Injectable({
  providedIn: 'root'
})

export class NavbarComponent implements OnInit {

  ngOnInit(): void {
      
  }

  @Input() menuItems: string[] = [
    "HOME", "ANALYTICS"
  ];

  

}
