import os
import asyncio
import logging
import requests
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from sendgrid import SendGridAPIClient
from utils.email_unsubscribe import get_unsubscribe_footer
from sendgrid.helpers.mail import (
    Mail, ReplyTo, From, TrackingSettings, ClickTracking, OpenTracking
)
from outreach_module.email_sending_class import EmailSender

load_dotenv(override=True)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_EMAIL_FROM = "antony@adeptech.co.ke" 
SENDGRID_EMAIL_FROM_NAME = "Antony Ngatia"
SENDGRID_REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
SENDGRID_REPLY_TO_NAME = "Antony Ngatia" 
SERVER_URL = os.getenv("SERVER_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SendGridSender(EmailSender):
    def __init__(self):
        pass
    
    async def create_client(self,api_key=SENDGRID_API_KEY):
        sendgrid_client = SendGridAPIClient(api_key)
        return sendgrid_client

    async def create_mail(self, email_to, subject, content, unsubscribe_token):
        unsubscribe_footer = get_unsubscribe_footer(SERVER_URL, unsubscribe_token)
        full_content = content + unsubscribe_footer

        email = Mail(
            from_email=SENDGRID_EMAIL_FROM,
            to_emails=email_to,
            subject=subject,
            html_content=full_content,
        )
        return email

    async def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        unsubscribe_token: str,
        frm=SENDGRID_EMAIL_FROM,
    ):

        email_headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}"
        }

        email = await self.create_mail(
            email_to=to,
            subject=subject,
            content=content,
            unsubscribe_token=unsubscribe_token
        )
        sendgrid_client = await self.create_client()

        # Add who to reply to
        email.reply_to = ReplyTo(
            email=SENDGRID_REPLY_TO_EMAIL,
            name=SENDGRID_REPLY_TO_NAME
        )

        # Add who the email is from
        email.from_email = From(
            email=frm,
            name=SENDGRID_EMAIL_FROM_NAME
        )
        
        # Add email settings
        email.tracking_settings = TrackingSettings(
            click_tracking=ClickTracking(enable=True, enable_text=True),
            open_tracking=OpenTracking(enable=True)
        )
        
        # Send Email
        response = sendgrid_client.send(email)
        logger.info(f"Email sent to {to}")

        return response

if __name__ == "__main__":
    async def main():
        sg = SendGridSender()
        await sg.send_email(
            to="m10mathenge@gmail.com",
            subject="Bossy!",
            content="Oyaaaa",
            unsubscribe_token="123"
        )

    asyncio.run(main())