import os, base64
import logging
from enum import Enum
from typing import List
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
from utils.email_prompts import email_prompts
import aiofiles,asyncio
import email_attachments 
from services.db_service import *

load_dotenv(override=True)
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
EMAIL_FROM = "mark.mathenge@adept-techno.com" 
REPLY_TO_EMAIL = "mark.mathenge@adept-techno.com"
REPLY_TO_NAME = "Mark Mathenge"

email_headers = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}"
}
async def send_email(
        data_source: str,
        email_to: str,
        first_name: str,
        company_name: str,
        extra_info: str, #Funding info, hiring area or event name
        email_from = EMAIL_FROM
):
    sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)

    if data_source == 'funding':
        funding_data = email_prompts.get('funding')
        subject = funding_data.get('subject')
        content = funding_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            funding_round = extra_info.title(),
        )
    elif data_source == 'hiring':
        hiring_data = email_prompts.get('hiring')
        subject = hiring_data.get('subject')
        content = hiring_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            hiring_area = extra_info.title()
        )
    elif data_source == 'events':
        hiring_data = email_prompts.get('events')
        subject = hiring_data.get('subject')
        content = hiring_data.get('content').format(
            first_name = first_name.title(),
            company_name = company_name.title(),
            event_name = extra_info.title()
        )

    email = Mail(
        from_email=email_from, 
        to_emails=email_to,
        subject=subject,
        html_content=content,
        )

    #Add who to reply to
    email.reply_to = ReplyTo(
        email=REPLY_TO_EMAIL,
        name=REPLY_TO_NAME
    )
    
    #Add email settings
    email.tracking_settings = TrackingSettings(
        click_tracking=ClickTracking(enable=True, enable_text=True),
        open_tracking=OpenTracking(enable=True)
    )

    #Add attachments
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(BASE_DIR, "email_attachments", "Adept Company 1 Pager.pdf")
    async with aiofiles.open(pdf_path, "rb") as file:
        data = await file.read()
        encoded_file = base64.b64encode(data).decode()

    email.attachment = [
        Attachment(
            file_content=(encoded_file),
            file_name=FileName("Adept Company 1 Pager.pdf"),
            file_type=FileType("application/pdf"),
            disposition=Disposition("attachment"),

        )
    ]

    response = sendgrid_client.send(email)
    logger.info(f"Email sent to {email_to}")
    return response

if __name__ == "__main__":
    async def main():
        response = await send_email(
            data_source='funding',
            email_to = 'm10mathenge@gmail.com',
            first_name = 'Antony',
            company_name='Antech',
            extra_info = "Series A"
        )
        print(response.status_code)
        print(response.body)
        print(response.headers)
    
    asyncio.run(main())