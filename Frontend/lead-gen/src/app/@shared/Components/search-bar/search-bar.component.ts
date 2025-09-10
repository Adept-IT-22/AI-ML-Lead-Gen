import { Component, Output } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ButtonComponent } from "../button/button.component";
import { FormsModule, NgModel } from '@angular/forms';
import { EventEmitter } from '@angular/core';

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, ButtonComponent, FormsModule],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.scss'
})
export class SearchBarComponent {
  query: string = '';
  @Output() search = new EventEmitter()

  onSearch() {
    this.search.emit(this.query.trim())
  }
}
