import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UnsubscribeService } from '../../@shared/Services/unsubscribe.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-unsubscribe',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './unsubscribe.component.html',
  styleUrls: ['./unsubscribe.component.scss']
})
export class UnsubscribeComponent implements OnInit {
  token: string = '';
  state: 'confirm' | 'processing' | 'success' | 'error' = 'confirm';
  errorMessage: string = '';

  constructor(
    private route: ActivatedRoute,
    private unsubscribeService: UnsubscribeService
  ) { }

  ngOnInit() {
    this.token = this.route.snapshot.queryParams['token'] || '';

    if (!this.token) {
      this.state = 'error';
      this.errorMessage = 'Invalid unsubscribe link. No token provided.';
    }
  }

  confirmUnsubscribe() {
    this.state = 'processing';

    this.unsubscribeService.unsubscribe(this.token).subscribe({
      next: (response) => {
        if (response.success) {
          this.state = 'success';
        } else {
          this.state = 'error';
          this.errorMessage = response.message || 'Failed to unsubscribe';
        }
      },
      error: (error) => {
        this.state = 'error';
        this.errorMessage = error.error?.message || 'An error occurred while processing your request';
      }
    });
  }

  cancelUnsubscribe() {
    // Just redirect or show a message
    this.state = 'confirm';
  }
}
