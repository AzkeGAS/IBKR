from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading, time
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
            bar.volume,
            reqId
        ])

def run_loop(app):
    app.run()

# --------------------------------------------------
app = IBApp()
app.connect("127.0.0.1", 7497, clientId=20)
threading.Thread(target=run_loop, args=(app,), daemon=True).start()
time.sleep(1)

# --------------------------------------------------
def mini_dax_contract(yyyymm):
    c = Contract()
    c.symbol = "FDXM"
    c.secType = "FUT"
    c.exchange = "EUREX"
    c.currency = "EUR"
    c.lastTradeDateOrContractMonth = yyyymm
    c.multiplier = "5"
    return c

# --------------------------------------------------
start_year = 2021
end_year = 2026
contracts = quarterly_contracts(start_year, end_year)

reqId = 1

for cm in contracts:
    expiry = datetime.strptime(cm + "15", "%Y%m%d")
    roll = expiry - timedelta(days=7)

    start = roll - timedelta(days=90)
    end = roll

    while end > start:
        app.reqHistoricalData(
            reqId=reqId,
            contract=mini_dax_contract(cm),
            endDateTime=end.strftime("%Y%m%d %H:%M:%S"),
            durationStr="1 W",
            barSizeSetting="3 mins",
            whatToShow="TRADES",
            useRTH=0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        reqId += 1
        time.sleep(12)   # ✅ pacing safe
        end -= timedelta(weeks=1)

# --------------------------------------------------
df = pd.DataFrame(
    app.data,
    columns=["DateTime", "Open", "High", "Low", "Close", "Volume", "ContractID"]
)

df["DateTime"] = pd.to_datetime(df["DateTime"])
df.sort_values("DateTime", inplace=True)
df.to_csv("FDXM_continuous_3min.csv", index=False)

app.disconnect()
print("✅ Continuous Mini‑DAX saved")
