import config
import threading
import time
import pandas as pd
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from Telegram import send_telegram

class IBTradingBot(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        # ---- DATAFRAME ----
        self.df = pd.DataFrame(columns=['time','open','high','low','close','volume'])


    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        print("Connected. NextOrderId:", orderId)

        self.request_history()

        send_telegram("✅ Connected/ Reconnected to IB")

    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")

    @staticmethod
    def get_contract() -> Contract:

        contract = Contract()
        contract = config.contract

        return contract


    def request_history(self):
        self.reqHistoricalData(
            reqId=1,
            contract=self.get_contract(),
            endDateTime="",
            durationStr="60 D",
            barSizeSetting="3 mins",
            whatToShow="MIDPOINT",
            useRTH=False,
            formatDate=1,
            keepUpToDate=True,
            chartOptions=[]
        )

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical Data Ended for {reqId}. Started at {start}, ending at {end}")

    def historicalData(self, reqId, bar):
        self.append_bar(bar)

    def append_bar(self, bar):
        new_row = {
            "time": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        }
        self.df.loc[len(self.df)] = new_row
        
        print(self.df.tail(1))
        self.df.to_csv("DAX_Raw_Data.csv", index=True)

# ---------------- RUN ----------------
def run_loop():
    app.run()

def connection_watchdog(app):
    while True:
        if not app.isConnected():
            send_telegram("⚠️ Connection lost detected")

            try:
                app.disconnect()
            except:
                pass

            time.sleep(2)

            app.connect("127.0.0.1", 7497, clientId=1)

            #threading.Thread(target=app.run, daemon=True).start()

        time.sleep(1)

if __name__ == "__main__":
    app = IBTradingBot()
    app.connect("127.0.0.1", 7497, clientId=1)

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