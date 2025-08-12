import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")
BASE_URL = os.getenv("PUBLIC_URL")  # например: https://english-talking-bot.onrender.com
SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")  # секрет заголовка

if not TOKEN or not WEBHOOK_SECRET_PATH or not BASE_URL:
    raise ValueError("TELEGRAM_TOKEN / WEBHOOK_SECRET_PATH / PUBLIC_URL must be set")

if not BASE_URL.startswith("https://"):
    raise ValueError("PUBLIC_URL must start with https://")

WEBHOOK_URL = f"{BASE_URL.rstrip('/')}/{WEBHOOK_SECRET_PATH}"
url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"

print(f"Registering webhook at: {WEBHOOK_URL}")

data = {
    "url": WEBHOOK_URL,
    "allowed_updates": json.dumps([
        "message", "edited_message", "callback_query", "pre_checkout_query"
    ]),
    "drop_pending_updates": "true",
}
if SECRET_TOKEN:
    data["secret_token"] = SECRET_TOKEN

try:
    response = requests.post(url, data=data, timeout=20)
    response.raise_for_status()
    print("✅ Webhook successfully set!", response.json())
except requests.RequestException as e:
    print("❌ Failed to set webhook:", e)
    if "response" in locals() and response is not None:
        print("Telegram response:", response.text)
