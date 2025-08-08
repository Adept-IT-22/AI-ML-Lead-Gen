import { Component, Injectable, Input, OnInit } from '@angular/core';
import { SearchBarComponent } from "../search-bar/search-bar.component";

@Component({
  selector: 'app-navbar',
  imports: [SearchBarComponent],
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
