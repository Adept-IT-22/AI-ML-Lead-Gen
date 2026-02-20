import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { INote } from '../../Libs/interfaces/note.interface';

@Injectable({
    providedIn: 'root'
})
export class NotesService {
    private readonly backend_url: string = `${environment.API_URL}`;
    private http = inject(HttpClient);

    saveNote(companyId: number, note: string): Observable<INote> {
        return this.http.post<INote>(`${this.backend_url}/save-note/${companyId}`, { note });
    }

    deleteNote(noteId: string): Observable<any> {
        return this.http.delete(`${this.backend_url}/delete-note/${noteId}`);
    }
}
