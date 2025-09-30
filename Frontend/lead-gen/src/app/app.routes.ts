import { Routes } from '@angular/router';
import { HomeComponent } from './Pages/home/home.component';
import { AnalyticsComponent } from './Pages/analytics/analytics.component';
import { LeadsTableComponent } from './@shared/Components/leads/leads.component'; 
import { LeadsPageComponent } from './Pages/leads-page/leads-page.component';
import { EventsComponent} from './Pages/events/events.component';
import { EngagementComponent } from './Pages/engagement/engagement.component';
import { SettingsComponent } from './@shared/Components/settings/settings.component';

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

    {
        path: 'events',
        component: EventsComponent
    },

    {
        path: 'engagement',
        component: EngagementComponent
    },  

    {
        path: 'settings',
        component: SettingsComponent
    },
];
