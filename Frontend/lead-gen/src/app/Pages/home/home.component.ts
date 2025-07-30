import { Component } from '@angular/core';
import { DataCardComponent } from "../../@shared/Components/data-card/data-card.component";
import { SearchBarComponent } from '../../@shared/Components/search-bar/search-bar.component';

@Component({
  selector: 'app-home',
  imports: [SearchBarComponent, DataCardComponent],
  standalone: true,
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {

}
