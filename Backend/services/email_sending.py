import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
from utils.email_prompts import email_prompts

load_dotenv(override=True)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
EMAIL_FROM = "mark.mathenge@adept-techno.com"

email_headers = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}"
}

def send_email(
        data_source: str,
        email_to: str,
        first_name: str,
        company_name: str,
        funding_round = None,
        hiring_area = None,
        event_name = None,
        email_from = EMAIL_FROM
):
    sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)

    if data_source == 'funding':
        funding_data = email_prompts.get('funding')
        subject = funding_data.get('subject')
        content = funding_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            funding_round = funding_round.title(),
        )
    elif data_source == 'hiring':
        hiring_data = email_prompts.get('hiring')
        subject = hiring_data.get('subject')
        content = hiring_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            hiring_area = hiring_area.title()
        )
    elif data_source == 'events':
        hiring_data = email_prompts.get('hiring')
        subject = hiring_data.get('subject')
        content = hiring_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            event_name = event_name.title()
        )

    email = Mail(
        from_email=email_from, 
        to_emails=email_to,
        subject=subject,
        plain_text_content=content,
        )
        
    response = sendgrid_client.send(email)
    return response

if __name__ == "__main__":
    response = send_email(
        data_source='funding',
        subject=subject,
        email_to = 'm10mathenge@gmail.com',
        first_name = 'Mark',
        company_name='Adept',
        funding_round='Series A',
        email_from=EMAIL_FROM
    )
    print(response.status_code)
    print(response.body)
    print(response.headers)


