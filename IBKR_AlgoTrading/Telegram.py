import requests

TELEGRAM_TOKEN = "8694994833:AAEVdIbET9Y3d6cVovLA7XeUDnkVLc5RWLY"
CHAT_ID = "8519724164"

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

