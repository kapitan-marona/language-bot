import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")
BASE_URL = "https://english-talking-bot.onrender.com"  # Render URL

if not TOKEN or not WEBHOOK_SECRET_PATH:
    raise ValueError("TELEGRAM_TOKEN or WEBHOOK_SECRET_PATH is missing from .env")

WEBHOOK_URL = f"{BASE_URL}/{WEBHOOK_SECRET_PATH}"
url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"

print(f"Registering webhook at: {WEBHOOK_URL}")

try:
    response = requests.post(url, data={"url": WEBHOOK_URL})
    response.raise_for_status()
    print("✅ Webhook successfully set!")
except requests.RequestException as e:
    print("❌ Failed to set webhook:", e)
    if response is not None:
        print("Telegram response:", response.text)
