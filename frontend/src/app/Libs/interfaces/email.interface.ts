export interface IEmail{
    body: string;
    subject: string;
    first_name: string;
    last_name: string;
    sent_at: string | null;
    status: string;
}