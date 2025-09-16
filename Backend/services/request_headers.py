import fake_useragent
from typing import Dict

# Initialize User Agent
session_user_agent = None

def get_header() -> Dict[str, str]:
    """
    Generates and returns a comprehensive set of HTTP headers to mimic a browser.
    
    This function creates a robust "fingerprint" by including a wide range of
    headers that a typical browser sends, which is crucial for bypassing
    advanced anti-bot measures that look beyond just the User-Agent.
    """
    global session_user_agent
    if session_user_agent is None:
        try:
            # Get a random user agent from a list of real browsers
            ua = fake_useragent.UserAgent()
            session_user_agent = ua.random
        except Exception:
            # Fallback user agent if the library fails
            session_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    
    # A comprehensive list of headers to make the request appear more human-like
    return {
        "User-Agent": session_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.finsmes.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
