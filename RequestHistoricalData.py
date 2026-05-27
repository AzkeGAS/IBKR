from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import pandas as pd
import threading
import time

class IBHistoricalData(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.data = {1: [], 2: [], 3: []}

    def historicalData(self, reqId, bar):
        self.data[reqId].append({
            "datetime": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        })

    def historicalDataEnd(self, reqId, start, end):
        print(f"Request {reqId} finished")

    def error(self, reqId, errorCode, errorString):
        print(f"Error {reqId}: {errorCode} - {errorString}")


def create_contract(symbol="AAPL", secType="STK", exchange="SMART", currency="USD"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = secType
    contract.exchange = exchange
    contract.currency = currency
    return contract


def run_loop(app):
    app.run()


# ---------- MAIN ----------
app = IBHistoricalData()
app.connect("127.0.0.1", 7497, clientId=1)

thread = threading.Thread(target=run_loop, args=(app,), daemon=True)
thread.start()

time.sleep(2)

contract = create_contract()

# ---- Request 1D data (500 days) ----
app.reqHistoricalData(
    reqId=1,
    contract=contract,
    endDateTime="",
    durationStr="365 D",
    barSizeSetting="1 day",
    whatToShow="TRADES",
    useRTH=1,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)

time.sleep(5)

# ---- Request 1H data (500 days) ----
app.reqHistoricalData(
    reqId=2,
    contract=contract,
    endDateTime="",
    durationStr="365 D",
    barSizeSetting="1 hour",
    whatToShow="TRADES",
    useRTH=1,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)

time.sleep(10)

# ---- Request 1H data (500 days) ----
app.reqHistoricalData(
    reqId=3,
    contract=contract,
    endDateTime="",
    durationStr="365 D",
    barSizeSetting="3 min",
    whatToShow="TRADES",
    useRTH=1,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)

time.sleep(15)

app.disconnect()

# ---------- Convert to DataFrames ----------

df_D = pd.DataFrame(app.data[1])
df_H = pd.DataFrame(app.data[2])
df_M = pd.DataFrame(app.data[3])

# Convert datetime column
df_D['datetime'] = pd.to_datetime(df_D['datetime'])
df_H['datetime'] = pd.to_datetime(df_H['datetime'])
df_M['datetime'] = pd.to_datetime(df_M['datetime'])

df_D.set_index("datetime", inplace=True)
df_H.set_index("datetime", inplace=True)
df_M.set_index("datetime", inplace=True

print("Daily Data:")
print(df_D.tail())

print("\nHourly Data:")
print(df_H.tail())


# Robust 1H Data Collector (Chunked)
from datetime import datetime, timedelta

def request_hourly_chunks(app, contract):
    end = ""
    all_data = []

    for i in range(20):  # ~500 days / 30
        req_id = 100 + i

        app.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime=end,
            durationStr="30 D",
            barSizeSetting="1 hour",
            whatToShow="TRADES",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        time.sleep(3)

        all_data += app.data.get(req_id, [])

        if len(app.data.get(req_id, [])) > 0:
            earliest = app.data[req_id][0]["datetime"]
            end = earliest  # step back in time

    return pd.DataFrame(all_data)
``
