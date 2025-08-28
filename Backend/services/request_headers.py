import fake_useragent

# Initialize User Agent
session_user_agent = None

# Get header
def get_header():
    global session_user_agent
    if session_user_agent is None:
        try:
            ua = fake_useragent.UserAgent()
            session_user_agent = ua.random
        except Exception as e:
            session_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    return {"User-Agent": session_user_agent}