import os
import logging
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, ReplyTo, From, TrackingSettings, ClickTracking, OpenTracking
)
import asyncio
from services.db_service import *
from utils.prompts.email_generation_prompt import get_email_generation_prompt

load_dotenv(override=True)
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SEND_API = "https://api.sendgrid.com/v3/mail/send"
EMAIL_FROM = "antony@adeptech.co.ke" 
EMAIL_FROM_NAME = "Antony Ngatia"
REPLY_TO_EMAIL = "antony@adeptech.co.ke" 
REPLY_TO_NAME = "Antony Ngatia" 
SERVER_URL = os.getenv("SERVER_URL")

email_headers = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}"
}
async def send_email(
        email_to: str,
        subject: str,
        content: str,
        unsubscribe_token: str,
        email_from = EMAIL_FROM
):
    sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
    
    # Add unsubscribe footer to email content
    unsubscribe_footer = f"""
    <br><br>
    <hr style="border: 1px solid #ddd;">
    <p style="font-size: 12px; color: #666;">
        If you no longer wish to receive these emails, 
        <a href="{SERVER_URL}/unsubscribe?token={unsubscribe_token}">
            click here to unsubscribe
        </a>.
    </p>
    """
    
    full_content = content + unsubscribe_footer
    
    email = Mail(
        from_email=email_from, 
        to_emails=email_to,
        subject=subject,
        html_content=full_content,
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
    import json
    from outreach_module.ai_email_generation import call_gemini_api
    async def main():
        company_description = """
        Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, 
        particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software 
        that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads 
        to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform 
        for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform 
        efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, 
        which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include 
        creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed 
        at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance 
        their sales strategies through AI-driven insights.
        """
        first_name = "Mark"
        company_name = "Adept"
        trigger_type = "funding"
        funding_round = "seed"
        sequence_number = 1
        
        prompt = get_email_generation_prompt(
            company_description=company_description,
            first_name = first_name,
            company_name=company_name,
            trigger_type=trigger_type,
            sequence_number=sequence_number,
            funding_round=funding_round
        )
        ai_response = await call_gemini_api(prompt)

        try:
            text = ai_response.candidates[0].content.parts[0].text
            email_json = json.loads(text)

            subject = email_json["subject"]
            content = email_json["content"]
            print(content)

            #response = await send_email(
                #email_to = 'm10mathenge@gmail.com',
                #subject= subject,
                #content= content,
                #unsubscribe_token = "e3a3c375-cde9-420b-9001-2b188cb2fac8"
            #)
            #print(response.status_code)
            #print(response.body)
            #print(response.headers)
        except Exception as e:
            error_msg = f"Couldn't send email: {e}"
            if hasattr(e, 'body'):
                error_msg += f" | SendGrid Body: {e.body}"
            logger.exception(error_msg)
    
    asyncio.run(main())
