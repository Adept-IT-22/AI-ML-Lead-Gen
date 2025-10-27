import { Component, OnInit, Renderer2 } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './@shared/Components/navbar/navbar.component';
import { SettingsService } from './@shared/Services/settings.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Lead Gen';
  currentTheme = 'retro-green-theme'; // default
  lightTheme = 'light-theme';
  darkTheme = 'retro-green-theme';

  constructor(
    private settingsService: SettingsService,
    private renderer: Renderer2
  ) {
    this.settingsService.loadSettings();
  }

  ngOnInit() {
    const savedTheme = localStorage.getItem('selectedTheme') || this.darkTheme;
    this.applyTheme(savedTheme);
  }

  toggleTheme() {
    const newTheme =
      this.currentTheme === this.darkTheme ? this.lightTheme : this.darkTheme;
    this.applyTheme(newTheme);
  }

  applyTheme(theme: string) {
    // Remove old class and apply new
    this.renderer.removeClass(document.body, this.currentTheme);
    this.renderer.addClass(document.body, theme);
    this.currentTheme = theme;
    localStorage.setItem('selectedTheme', theme);
  }
}
