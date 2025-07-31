import { Routes } from '@angular/router';
import { HomeComponent } from './Pages/home/home.component';

export const routes: Routes = [
    {
    path: 'home',
    loadComponent: () =>
      import('./Pages/home/home.component').then((m) => m.HomeComponent),
    }
];
