// libs/interfaces/settings.interface.ts
export interface ISettings {
  theme: 'light' | 'dark';
  language: string;
  timezone: string;
  notifications: {
    email: boolean;
    sms: boolean;
    inApp: boolean;
  };
  exportFormat: 'pdf' | 'excel' | 'csv';
}
