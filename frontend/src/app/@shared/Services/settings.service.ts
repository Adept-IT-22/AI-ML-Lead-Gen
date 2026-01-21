// services/settings.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ISettings } from '../../Libs/interfaces/settings.interface';

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private defaultSettings: ISettings = {
    theme: 'light',
    language: 'en',
    timezone: 'UTC',
    notifications: { email: true, sms: false, inApp: true },
    exportFormat: 'excel'
  };

  private settingsSubject = new BehaviorSubject<ISettings>(this.defaultSettings);
  settings$ = this.settingsSubject.asObservable();

  getSettings(): ISettings {
    return this.settingsSubject.value;
  }

  updateSettings(newSettings: Partial<ISettings>) {
    const updated = { ...this.settingsSubject.value, ...newSettings };
    this.settingsSubject.next(updated);
    localStorage.setItem('app_settings', JSON.stringify(updated)); // persist
  }

  loadSettings() {
    const saved = localStorage.getItem('app_settings');
    if (saved) {
      this.settingsSubject.next(JSON.parse(saved));
    }
  }
}
