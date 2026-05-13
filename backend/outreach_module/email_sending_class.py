import os
import logging
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from sendgrid import SendGridAPIClient
from utils.email_unsubscribe import get_unsubscribe_footer
from sendgrid.helpers.mail import (
    Mail, ReplyTo, From, TrackingSettings, ClickTracking, OpenTracking
)

load_dotenv(override=True)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
EMAIL_FROM = "antony@adeptech.co.ke" 
EMAIL_FROM_NAME = "Antony Ngatia"
REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
REPLY_TO_NAME = "Antony Ngatia" 
SERVER_URL = os.getenv("SERVER_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailSender(ABC):
    """
    Abstract class for sending emails. Decouples email sending from any specific email sender.
    """

    @abstractmethod
    def send_email(self):
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
        self.email_to = email_to
        self.subject = subject
        self.content = content
        self.unsubscribe_token = unsubscribe_token

    def create_client(self):
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        return sendgrid_client

    def create_mail(self):
        unsubscribe_footer = get_unsubscribe_footer(SERVER_URL, self.unsubscribe_token)
        full_content = self.content + unsubscribe_footer

        email = Mail(
            from_email=EMAIL_FROM,
            to_emails=self.email_to,
            subject=self.subject,
            html_content=full_content,
        )
        return email

    def send_email(self):
        email = self.create_mail()
        sendgrid_client = self.create_client()

        # Add who to reply to
        email.reply_to = ReplyTo(
            email=REPLY_TO_EMAIL,
            name=REPLY_TO_NAME
        )

        email.from_email = From(
            email=EMAIL_FROM,
            name=EMAIL_FROM_NAME
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