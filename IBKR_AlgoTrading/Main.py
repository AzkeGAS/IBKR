from Historical_Data import HistData, run_loop, connection_watchdog
import threading
from Telegram import send_telegram

if __name__ == "__main__":

    # --- IBKR ---
    ib = HistData()
    ib.connect("127.0.0.1", 7497, 10)

    # IB thread
    threading.Thread(target=run_loop, args=(ib,), daemon=True).start()

    # Watchdog thread
    threading.Thread(target=connection_watchdog, args=(ib,), daemon=True).start()

    send_telegram(">>> Bot Running...")
    
    try:
        while True:

            # --- REQUEST DATA ---
            contract = HistData.get_contract()
            ib.get_historical_data(100, contract)
            df_3m = ib.get_dataframes(100)

    except KeyboardInterrupt:
        ib.disconnect()
        send_telegram(">>> Bot Deconnected Manually...")

