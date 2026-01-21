interface CompanyDetails {
  name: string;
  contactPerson?: string;
  newRemarks?: string;
  previousRemarks?: string;
  [key: string]: any; // optional if you still want flexibility
}