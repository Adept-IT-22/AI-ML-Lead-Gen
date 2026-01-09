import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CompaniesService } from '../../@shared/Services/companies.service';
import { IEmail } from '../../Libs/interfaces/email.interface';
import { NgIf, NgFor } from '@angular/common';

@Component({
  standalone: true,
  imports: [NgIf, NgFor],
  selector: 'app-emails',
  templateUrl: './emails.component.html',
  styleUrls: ['./emails.component.scss']
})
export class EmailsComponent implements OnInit {
  companyId!: number;
  emails: IEmail[] = [];
  loading = true;
  error?: string;

  constructor(private route: ActivatedRoute, private companiesService: CompaniesService) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(pm => {
      const idParam = pm.get('company_id');
      if (!idParam) {
        this.error = 'No company id provided';
        this.loading = false;
        return;
      }
      this.companyId = Number(idParam);
      this.companiesService.viewSentEmails(this.companyId).subscribe({
        next: (data) => {
          this.emails = Array.isArray(data) ? data : [data];
          // add a plain text version of the body using DOM parsing with a regex fallback
          this.emails = this.emails.map((e: any) => ({
            ...e,
            plainBody: this.stripHtml(e.body || e.preview_text || e.content || '')
          }));
          this.loading = false;
        },
        error: (err) => {
          console.error(err);
          this.error = 'Failed to fetch emails';
          this.loading = false;
        }
      });
    });
  }

  private stripHtml(html: string): string {
    if (!html) return '';
    try {
      // Use DOMParser in the browser to safely extract text content
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      // innerText preserves visible line breaks and paragraph structure
      const text = (doc.body.innerText || doc.body.textContent || '');
      // normalize CRLF to LF and collapse excessive blank lines to at most one empty line
      return text.replace(/\r\n?/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
    } catch (e) {
      // Fallback: simple regex to remove tags (best-effort)
      return html
        .replace(/<br\s*\/?>(\s*)/gi, '\n')
        .replace(/<\/p>(\s*)/gi, '\n\n')
        .replace(/<[^>]*>/g, '')
        .replace(/\r\n?/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
    }
  }
}
