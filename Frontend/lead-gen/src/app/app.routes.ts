import { Routes } from '@angular/router';
import { HomeComponent } from './Pages/home/home.component';
import { AnalyticsComponent } from './Pages/analytics/analytics.component'; 

export const routes: Routes = [
    {
        path: '',
        component: HomeComponent
    },    
    {
        path: 'analytics',
        component: AnalyticsComponent
    }
];
