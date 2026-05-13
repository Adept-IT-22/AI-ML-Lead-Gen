import os
import logging
import requests
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from sendgrid import SendGridAPIClient
from utils.email_unsubscribe import get_unsubscribe_footer
from sendgrid.helpers.mail import (
    Mail, ReplyTo, From, TrackingSettings, ClickTracking, OpenTracking
)

load_dotenv(override=True)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_EMAIL_FROM = "antony@adeptech.co.ke" 
SENDGRID_EMAIL_FROM_NAME = "Antony Ngatia"
SENDGRID_REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
SENDGRID_REPLY_TO_NAME = "Antony Ngatia" 

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_EMAIL_SEND_API = "https://api.brevo.com/v3/smtp/email"
BREVO_EMAIL_FROM = "antony@adeptech.co.ke" 
BREVO_EMAIL_FROM_NAME = "Antony Ngatia"
BREVO_REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
BREVO_REPLY_TO_NAME = "Antony Ngatia" 

SERVER_URL = os.getenv("SERVER_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailSender(ABC):
    """
    Abstract class for sending emails. Decouples email sending from any specific email sender.
    """
    def __init__(self, email_to: str, subject: str, content: str, unsubscribe_token: str):
        self.email_to = email_to
        self.subject = subject
        self.content = content
        self.unsubscribe_token = unsubscribe_token

    @abstractmethod
    def send_email(self, to: str, frm: str, subject: str, content: str):
        """
        Send email. Raise if not called.
        """
        raise NotImplementedError

class SendGridSender(EmailSender):
    def __init__(
        self, 
        email_to: str,
        subject: str,
        content: str,
        unsubscribe_token: str
    ):
        super().__init__(email_to, subject, content, unsubscribe_token)

    def create_client(self):
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        return sendgrid_client

    def create_mail(self):
        unsubscribe_footer = get_unsubscribe_footer(SERVER_URL, self.unsubscribe_token)
        full_content = self.content + unsubscribe_footer

        email = Mail(
            from_email=SENDGRID_EMAIL_FROM,
            to_emails=self.email_to,
            subject=self.subject,
            html_content=full_content,
        )
        return email

    def send_email(
        self,
        to=None,
        frm=None,
        subject=None,
        content=None
    ):
        to = to or self.email_to
        subject = subject or self.subject
        content = content or self.content

        email_headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}"
        }

        email = self.create_mail()
        sendgrid_client = self.create_client()

        # Add who to reply to
        email.reply_to = ReplyTo(
            email=SENDGRID_REPLY_TO_EMAIL,
            name=SENDGRID_REPLY_TO_NAME
        )

        # Add who the email is from
        email.from_email = From(
            email=SENDGRID_EMAIL_FROM,
            name=SENDGRID_EMAIL_FROM_NAME
        )
        
        # Add email settings
        email.tracking_settings = TrackingSettings(
            click_tracking=ClickTracking(enable=True, enable_text=True),
            open_tracking=OpenTracking(enable=True)
        )
        
        # Send Email
        response = sendgrid_client.send(email)
        logger.info(f"Email sent to {self.email_to}")

        return response

class BrevoSender(EmailSender):
    def __init__(
        self, 
        email_to: str,
        subject: str,
        content: str,
        unsubscribe_token: str
    ):
        super().__init__(email_to, subject, content, unsubscribe_token)

    def send_email(
        self,
        to=None,
        frm=None,
        subject=None,
        content=None
    ):
        to = to or self.email_to
        subject = subject or self.subject
        content = content or self.content
        
        unsubscribe_footer = get_unsubscribe_footer(SERVER_URL, self.unsubscribe_token)
        full_content = content + unsubscribe_footer

        payload = {
            "sender": {
                "name": BREVO_EMAIL_FROM_NAME,
                "email": BREVO_EMAIL_FROM
            },
            "to": [
                {
                    "email": to,
                    "name": to.split('@')[0]  # Use prefix as a default name
                }
            ],
            "subject": subject,
            "htmlContent": full_content
        }

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        response = requests.post(BREVO_EMAIL_SEND_API, json=payload, headers=headers)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent via Brevo to {to}")
        else:
            logger.error(f"Failed to send email via Brevo to {to}: {response.text}")

        return response

if __name__ == "__main__":
    bs = BrevoSender(email_to="m10mathenge@gmail.com", subject="Oya Niaje!", content="Salamu Tu!", unsubscribe_token="123")
    bs.send_email()