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
    async def main():
        response = await send_email(
            email_to = 'william.gateri@adept-techno.com',
            subject= "Greetings",
            content= "Hello"
        )
        print(response.status_code)
        print(response.body)
        print(response.headers)
    
    asyncio.run(main())


#if data_source == 'funding':
    #if latest_funding_round.lower() == 'seed':
        #funding_data = email_prompts.get('funding').get('seed')
        #subject = funding_data.get('subject')
        #content = funding_data.get('content').format(
            #first_name = first_name.title(),
        #)
    #elif latest_funding_round.lower() == 'series a' or latest_funding_round.lower() == 'series b':
        #funding_data = email_prompts.get('funding').get('series')
        #subject = funding_data.get('subject')
        #content = funding_data.get('content').format(
            #first_name = first_name.title(),
        #)
    #else:
        #funding_data = email_prompts.get('funding').get("generic")
        #subject = funding_data.get('subject')
        #content = funding_data.get('content').format(
            #first_name = first_name.title(),
            #company_name = company_name.title(),
            #funding_round = extra_info.title()
        #)

#elif data_source == 'hiring':
    #hiring_data = email_prompts.get('hiring')
    #subject = hiring_data.get('subject')
    #content = hiring_data.get('content').format(
        #first_name = first_name.title(),
        #company_name = company_name.title(),
        #hiring_area = extra_info.title()
    #)
#elif data_source == 'events':
    #event_data = email_prompts.get('events')
    #subject = event_data.get('subject')
    #content = event_data.get('content').format(
        #first_name = first_name.title(),
        #company_name = company_name.title(),
        #event_name = extra_info.title()
    #)
