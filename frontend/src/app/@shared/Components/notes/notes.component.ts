import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';
import { INote } from '../../../Libs/interfaces/note.interface';
import { NotesService } from '../../Services/notes.service';

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
  @Input() companyId!: number;
  @Input() notes: INote[] = [];

  private notesService = inject(NotesService);

  newNote: string = '';
  showPrevious = false;

  togglePreviousRemarks(): void {
    this.showPrevious = !this.showPrevious;
  }

  saveRemark(): void {
    if (this.newNote.trim()) {
      this.notesService.saveNote(this.companyId, this.newNote).subscribe({
        next: (savedNote) => {
          this.notes = [savedNote, ...this.notes];
          this.newNote = '';
          alert('Remark saved successfully!');
        },
        error: (err) => {
          console.error('Error saving note:', err);
          alert('Failed to save remark.');
        }
      });
    } else {
      alert('Please enter a remark before saving.');
    }
  }

  deleteNote(noteId: string): void {
    if (confirm('Are you sure you want to delete this note?')) {
      this.notesService.deleteNote(noteId).subscribe({
        next: () => {
          this.notes = this.notes.filter(n => n.id !== noteId);
          alert('Note deleted!');
        },
        error: (err) => {
          console.error('Error deleting note:', err);
          alert('Failed to delete note.');
        }
      });
    }
  }
}
