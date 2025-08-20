import os
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

headers = {
    "Content-Type": "application/json",
    "accept": "application/json",
    "Cache-Control": "no-cache",
    "x-api-key": APOLLO_API_KEY
}