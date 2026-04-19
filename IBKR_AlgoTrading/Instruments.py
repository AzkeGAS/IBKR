
from ibapi.contract import Contract

# ---------- DAX ----------
DAX_buffer = float(0)

DAX_contract = Contract()
DAX_contract.symbol = "DAX"
DAX_contract.secType = "FUT"
DAX_contract.exchange = "EUREX"
DAX_contract.currency = "EUR"
DAX_contract.multiplier = 5

DAX_contract.lastTradeDateOrContractMonth = "202606"
DAX_contract.tradingClass = "FDXM"   # 👈 MICRO DAX

# ---------- NG ----------
NG_buffer = float(0.005)

NG_contract = Contract()
NG_contract.symbol = "GQ"
NG_contract.secType = "FUT"
NG_contract.exchange = "NYMEX"
NG_contract.currency = "USD"
NG_contract.multiplier = 2500

NG_contract.lastTradeDateOrContractMonth = "202605"
NG_contract.tradingClass = "QG"   # 👈 Mini NG

# ---------- MES ----------
MES_buffer = float(0.25)

MES_contract = Contract()
MES_contract.symbol = "MES"
MES_contract.secType = "FUT"
MES_contract.exchange = "CME"
MES_contract.currency = "USD"
MES_contract.multiplier = 5

MES_contract.lastTradeDateOrContractMonth = "202606"
MES_contract.tradingClass = "MES"   # 👈 Micro E-Mini S&P 500 Stock Price Index









