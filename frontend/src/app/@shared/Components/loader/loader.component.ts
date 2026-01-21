import { Component } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'; // <-- Import Angular Material spinner

@Component({
  selector: 'app-loader',
  standalone: true,                         // ✅ Mark it standalone
  imports: [MatProgressSpinnerModule],      // ✅ Add spinner module
  templateUrl: './loader.component.html',
  styleUrls: ['./loader.component.scss']    // ✅ fixed typo
})
export class LoaderComponent {}
