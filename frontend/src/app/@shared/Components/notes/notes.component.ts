import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';

@Component({
  selector: 'app-notes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDividerModule
  ],
  templateUrl: './notes.component.html',
  styleUrls: ['./notes.component.scss']
})
export class NotesComponent {
  @Input() title: string = '';
  @Input() author: string = '';
  @Input() newRemarks: string = '';
  @Input() previousRemarks: string = '';

  newNote: string = '';
  showPrevious = false;

  togglePreviousRemarks(): void {
    this.showPrevious = !this.showPrevious;
  }

  saveRemark(): void {
    if (this.newNote.trim()) {
      this.previousRemarks = this.newRemarks || '';
      this.newRemarks = this.newNote;
      this.newNote = '';
      alert('Remark saved successfully!');
    } else {
      alert('Please enter a remark before saving.');
    }
  }

  deleteRemarks(): void {
    this.newRemarks = '';
    this.previousRemarks = '';
    this.newNote = '';
    alert('All remarks have been deleted.');
  }
}
