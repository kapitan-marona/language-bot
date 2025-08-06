# config/config.py
import os
import base64
import tempfile

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")

# Google credentials
GOOGLE_CREDENTIALS_BASE64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")

# config.py
ADMINS = [
    978646307
]



def create_google_credentials_file():
    if not GOOGLE_CREDENTIALS_BASE64:
        raise ValueError("Google credentials not found in env.")
    decoded = base64.b64decode(GOOGLE_CREDENTIALS_BASE64)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp.write(decoded)
    temp.close()
    return temp.name
