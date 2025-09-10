import { Routes } from '@angular/router';
import { HomeComponent } from './Pages/home/home.component';
import { AnalyticsComponent } from './Pages/analytics/analytics.component';
import { LeadsTableComponent } from './@shared/Components/leads/leads.component'; 
import { LeadsPageComponent } from './@shared/Components/leads-page/leads-page.component';

export const routes: Routes = [
    {
        path: '',
        component: HomeComponent
    },    
    {
        path: 'analytics',
        component: AnalyticsComponent
    },

    {   path: 'company/:id',
        loadComponent: () =>
            import('./@shared/Components/company-details/company-details.component').then(m => m.CompanyDetailsComponent),
    },

    {
        path: 'leads',
        component: LeadsPageComponent
    },
];
