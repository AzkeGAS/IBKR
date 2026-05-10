from time import time

from RealTimeTrading import IBTradingBot, run_loop, connection_watchdog
import threading
from Telegram import send_telegram

if __name__ == "__main__":
    app = IBTradingBot()
    app.connect("127.0.0.1", 7497, clientId=10)

    time.sleep(1)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    time.sleep(2)

    # Watchdog thread
    threading.Thread(target=connection_watchdog, args=(app,), daemon=True).start()

    try:

        while True:

            time.sleep(3)

    except KeyboardInterrupt:
        app.disconnect()
        send_telegram("🚨 Bot disconnected manually!")

