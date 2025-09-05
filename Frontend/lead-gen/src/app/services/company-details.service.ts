// company.service.ts
import { Injectable } from '@angular/core';

export interface CompanyField {
  label: string;
  value: string;
}

export interface CompanySection {
  section: string;
  fields: CompanyField[];
}

@Injectable({
  providedIn: 'root',
})
export class CompanyService {
  private companyDetails: { [key: string]: CompanySection[] } = {
    '01': [
      {
        section: 'Identity',
        fields: [
          { label: 'Company Name', value: 'Mbodi AI' },
          { label: 'Description', value: "Mbodi AI is an embodied AI platform that enhances industrial robotics by... [Read More]"},
          { label: 'Industry', value: 'Information Technology & Services' },
          { label: 'Location', value: 'New York, United States' },
        ],
      },
      {
        section: 'Online Presence',
        fields: [
          { label: 'Website', value: 'http://www.mbodi.ai' },
          { label: 'LinkedIn', value: 'http://www.linkedin.com/company/mbodiai' },
        ],
      },
      {
        section: 'Company Profile',
        fields: [
          { label: 'Year Founded', value: '2024' },
          { label: 'Number of Employees', value: '6' },
          { label: 'Total Funding', value: 'N/A' },
          { label: 'Annual Revenue', value: 'N/A' },
        ],
      },
      {
        section: 'Contacts',
        fields: [
          { label: 'Contact Person', value: 'Sebastian Peralta' },
          {label: 'Email', value: 'sebastian@mbodi.ai'},
          {label: 'LinkedIn', value: 'http://www.linkedin.com/sebbyjp'},
          {label: 'Position', value: 'Founder'},
          { label: 'Contacted Status', value: 'Uncontacted' },
        ],
      },
      {
        section: 'Scores & Metrics',
        fields: [
          { label: 'ICP Score', value: '70' },
          { label: 'Head-count growth in 6 Months', value: '1.0' },
          { label: 'Head-count growth in 12 Months', value: '2.0' },
        ],
      },
      {
        section: 'Technologies',
        fields: [
          {
            label: 'Technologies Used',
            value: 'GitHub Classroom, E-learning tools',
          },
          {
            label: 'Keywords',
            value: 'AI robotics, Automation, Scalable robotics, Software development'
          }
        ],
      },
    ],

    '02': [
      {
        section: 'Identity',
        fields: [
          { label: 'Company Name', value: 'Tech AI' },
          { label: 'Description', value: 'Fintech' },
          { label: 'Industry', value: 'Defense' },
          { label: 'Location', value: 'Nairobi, Kenya' },
        ],
      },
      {
        section: 'Online Presence',
        fields: [
          { label: 'Website', value: 'www.techai.com' },
          { label: 'LinkedIn', value: 'www.linkedin.com/Tech-ai' },
        ],
      },
      {
        section: 'Company Profile',
        fields: [
          { label: 'Year Founded', value: '2020' },
          { label: 'Total Funding', value: '$1.2M' },
          { label: 'Number of Employees', value: '60' },
          { label: 'Annual Revenue', value: '$800K' },
        ],
      },
      {
        section: 'Contacts',
        fields: [{ label: 'Contact Person', value: 'Mccarthy' }],
      },
      {
        section: 'Scores & Metrics',
        fields: [
          { label: 'ICP Score', value: '81' },
          { label: 'Head-count growth in 6 Months', value: '0.5' },
          { label: 'Head-count growth in 12 Months', value: '1.0' },
        ],
      },
      {
        section: 'Technologies',
        fields: [{ label: 'Technologies Used', value: 'AWS, React, Node.js' }],
      },
    ],
  };

  getCompanyDetails(id: string): CompanySection[] | null {
    return this.companyDetails[id] || null;
  }
}
