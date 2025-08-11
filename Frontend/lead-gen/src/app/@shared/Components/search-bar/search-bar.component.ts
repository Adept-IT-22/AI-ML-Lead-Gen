import { Component } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ButtonComponent } from "../button/button.component";

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, ButtonComponent],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.scss'
})
export class SearchBarComponent {

}
