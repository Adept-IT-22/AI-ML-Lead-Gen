import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { NgClass } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [MatButtonModule, RouterLink, NgClass, MatIconModule],
  templateUrl: './button.component.html',
  styleUrls: ['./button.component.scss']   // ✅ fixed
})
export class ButtonComponent {
  @Input() icon?: string;
  @Input() iconPosition: 'left' | 'right' = 'left';
  @Input() buttonType: 'button' | 'submit' = 'button';
  @Input() buttonText: string = '';
  @Input() buttonStyleClass: string = '';
  @Input() routerLink?: any[] | string;  // ✅ make routerLink work directly
  @Input() buttonLink: string = ''; // for external links
}
