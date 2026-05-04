from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import pandas as pd
from datetime import datetime, timedelta

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = []

    def historicalData(self, reqId, bar):
        self.data.append([
            bar.date,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume
        ])

    def historicalDataEnd(self, reqId, start, end):
        print(f"Finished request {reqId}: {start} -> {end}")

def run_loop(app):
    app.run()

# -------------------------------------------------

app = IBApp()
app.connect("127.0.0.1", 7497, clientId=1)

thread = threading.Thread(target=run_loop, args=(app,), daemon=True)
thread.start()

time.sleep(1)

# -------------------------------------------------
# Contract definition
contract = Contract()
contract.symbol = "FDAX"
contract.secType = "FUT"
contract.exchange = "EUREX"
contract.currency = "EUR"
contract.lastTradeDateOrContractMonth = "202506"
contract.multiplier = "25"


# -------------------------------------------------
# Request historical data in chunks
reqId = 1
end_date = datetime.utcnow()
start_limit = end_date - timedelta(days=365 * 5)

while end_date > start_limit:
    end_str = end_date.strftime("%Y%m%d %H:%M:%S")

    app.reqHistoricalData(
        reqId=reqId,
        contract=contract,
        endDateTime=end_str,
        durationStr="1 W",          # max safe window
        barSizeSetting="3 mins",
        whatToShow="TRADES",
        useRTH=0,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    reqId += 1
    time.sleep(12)  # ✅ pacing safety

    end_date -= timedelta(weeks=1)

# -------------------------------------------------
# Save result
df = pd.DataFrame(
    app.data,
    columns=["DateTime", "Open", "High", "Low", "Close", "Volume"]
)

df["DateTime"] = pd.to_datetime(df["DateTime"])
df.sort_values("DateTime", inplace=True)

df.to_csv("DAX_FUT_3min_5Y.csv", index=False)
print("Saved DAX_FUT_3min_5Y.csv")

app.disconnect()
