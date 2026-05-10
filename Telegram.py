import requests

TELEGRAM_TOKEN = "8788458922:AAG_-kjtx5ktDIvrDpiYGovOnSH3Me3lm7Q"
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

