import { Component } from '@angular/core';
import { SearchBarComponent } from "../../@shared/Components/search-bar/search-bar.component";
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";

@Component({
  selector: 'app-home',
  imports: [SearchBarComponent, DataCardComponent],
  standalone: true,
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {

}
