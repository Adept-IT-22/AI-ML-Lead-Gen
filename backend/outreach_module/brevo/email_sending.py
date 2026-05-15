import os
import asyncio
import logging
import requests
from brevo import AsyncBrevo, Configuration
from brevo.transactional_emails import(
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem
)
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from sendgrid import SendGridAPIClient
from utils.email_unsubscribe import get_unsubscribe_footer
from outreach_module.email_sending_class import EmailSender

load_dotenv(override=True)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_EMAIL_SEND_API = "https://api.brevo.com/v3/smtp/email"
BREVO_EMAIL_FROM = "antony@adeptech.co.ke" 
BREVO_EMAIL_FROM_NAME = "Antony Ngatia"
BREVO_REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
BREVO_REPLY_TO_NAME = "Antony Ngatia" 
SERVER_URL = os.getenv("SERVER_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BrevoSender(EmailSender):
    def __init__(self):
        pass

    async def create_client(self,api_key=BREVO_API_KEY):
        brevo_client = AsyncBrevo(api_key=api_key)
        return brevo_client

    async def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        unsubscribe_token: str,
        frm=BREVO_EMAIL_FROM,
    ):
        unsubscribe_footer = get_unsubscribe_footer(SERVER_URL, unsubscribe_token)
        full_content = content + unsubscribe_footer

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        brevo_client = await self.create_client()

        response = await brevo_client.transactional_emails.send_transac_email(
            subject=subject,
            html_content=full_content,
            sender=SendTransacEmailRequestSender(
                name=BREVO_EMAIL_FROM_NAME,
                email=frm
            ),
            to=[
                SendTransacEmailRequestToItem(
                    email=to,
                    name=to.split('@')[0]
                )
            ]
        )

        logger.info("Email sent. Message ID: %s", response.message_id)


if __name__ == "__main__":
    async def main():
        bs = BrevoSender()

        await bs.send_email(
            to="m10mathenge@gmail.com", 
            subject="Oya!", 
            content="Niambie boss!",
            unsubscribe_token="123"
        )
    asyncio.run(main())
