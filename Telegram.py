import requests

TELEGRAM_TOKEN = ""
CHAT_ID = ""

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

