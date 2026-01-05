import os
import logging
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
import asyncio
from services.db_service import *
from utils.prompts.email_generation_prompt import get_email_generation_prompt

load_dotenv(override=True)
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
EMAIL_FROM = "antony@adept-techno.co.ke" 
EMAIL_FROM_NAME = "Antony Ngatia"
REPLY_TO_EMAIL = "antony@adept-techno.co.ke" 
REPLY_TO_NAME = "Antony Ngatia" 

email_headers = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}"
}
async def send_email(
        email_to: str,
        subject: str,
        content: str ,
        email_from = EMAIL_FROM
):
    sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
    
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

    email.from_email = From(
        email=EMAIL_FROM,
        name=EMAIL_FROM_NAME
    )
    
    #Add email settings
    email.tracking_settings = TrackingSettings(
        click_tracking=ClickTracking(enable=True, enable_text=True),
        open_tracking=OpenTracking(enable=True)
    )

    response = sendgrid_client.send(email)
    logger.info(f"Email sent to {email_to}")
    return response

if __name__ == "__main__":
    from outreach_module.ai_email_generation import call_gemini_api
    async def main():
        response = await send_email(
            email_to = 'm10mathenge@gmail.com',
            subject= "Greetings",
            content= "Hello"
        )
        print(response.status_code)
        print(response.body)
        print(response.headers)
    
    asyncio.run(main())
