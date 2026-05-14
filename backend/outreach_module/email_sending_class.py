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

    @abstractmethod
    async def create_client(self, api_key):
        raise NotImplementedError

    @abstractmethod
    async def send_email(self, to: str, frm: str, subject: str, content: str, unsubscribe_token: str):
        """
        Send email. Raise if not called.
        """
        raise NotImplementedError
