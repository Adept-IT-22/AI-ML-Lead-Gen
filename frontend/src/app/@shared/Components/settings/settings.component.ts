// settings.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService } from '../../Services/settings.service';
import { ISettings } from '../../../Libs/interfaces/settings.interface';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html'
})
export class SettingsComponent {
  settings: ISettings;

  constructor(private settingsService: SettingsService) {
    this.settings = this.settingsService.getSettings();
  }

  save() {
    this.settingsService.updateSettings(this.settings);
    alert('Settings saved ✅');
  }
}
