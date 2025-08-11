import { Component } from '@angular/core';
import { DataFeedComponent } from "../../@shared/Components/data-feed/data-feed.component";

@Component({
  selector: 'app-analytics',
  imports: [DataFeedComponent],
  standalone: true,
  templateUrl: './analytics.component.html',
  styleUrl: './analytics.component.scss'
})
export class AnalyticsComponent {
  activity_feed = [
    '[2025-07-21] Lead 01 status changed to MQL',
    '[2025-07-21] New Lead 02 from Google News',
    '[2025-07-21] Meeting shcedule for lead 03'
  ];

}
