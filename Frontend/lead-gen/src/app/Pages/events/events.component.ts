import { Component, OnInit } from '@angular/core';
import { IEvent } from '../../Libs/interfaces/event.interface';
import { EventService } from '../../@shared/Services/event.service';
import { CommonModule } from '@angular/common';
import { NavbarComponent } from '../../@shared/Components/navbar/navbar.component';
import { FilterComponent } from '../../@shared/Components/filter/filter.component';
@Component({
  selector: 'app-events',
  standalone: true,
  imports: [CommonModule,FilterComponent],
  templateUrl: './events.component.html',
  styleUrl: './events.component.scss'
})
export class EventsComponent implements OnInit {
  events: IEvent[] = [];
  filteredEvents: IEvent[] = [];
  loading = true;

  activeFilters: Record<string, string[]> = {};

  // ✅ Define filters (you can add more sources here later)
  filters = [
  { optionType: 'BY WEBSITE', options: ['Eventbrite', 'Meetup', 'TechEvents', 'CustomSource'], key: 'source' },
  { optionType: 'BY ATTENDANCE', options: ['Online', 'Inperson'], key: 'attendance' },
  { optionType: 'BY DATE', options: [ 'january', 'february', 'march', 'april', 'may', 'june','july', 'august', 'september', 'october', 'november', 'december'], key: 'contacted_status' },
  { optionType: 'BY SOURCE', options: ['All', 'Funding', 'Hiring'], key: 'event_type' }

  ];

  constructor(private eventService: EventService) {}

  ngOnInit(): void {
    this.eventService.events().subscribe({
      next: (data) => {
        this.events = data;
        this.filteredEvents = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching events:', err);
        this.loading = false;
      }
    });
  }

  onFilterChange(event: { key: string; value: string }) {
    this.activeFilters[event.key] = event.value ? [event.value] : [];

    this.filteredEvents = this.events.filter(ev => {
      return Object.keys(this.activeFilters).every(key => {
        if (!this.activeFilters[key].length) return true;
        return this.activeFilters[key].includes((ev as any)[key]);
      });
    });
  }
}
