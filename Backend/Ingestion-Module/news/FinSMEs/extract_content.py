import os
import httpx
from lxml import etree
from dotenv import load_dotenv
import google.generativeai as genai

#Import env variables
load_dotenv(verbose=True, override=True)

#Gemini API Key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

