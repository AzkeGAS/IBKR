from ibapi.client import *
from ibapi.wrapper import *
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum
import threading

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.bid = None
        self.ask = None

    def nextValidId(self, orderId):
        self.orderId = orderId

        # Solicitar datos cuando ya tienes conexión válida
        self.reqMarketDataType(1)

        contract = Contract()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        self.reqMktData(self.orderId, contract, "", False, False, [])

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 1:  # BID
            self.bid = price
        elif tickType == 2:  # ASK
            self.ask = price

        # Calcular spread cuando ambos existen
        if self.bid is not None and self.ask is not None:
            spread = self.ask - self.bid
            print(f"Bid: {self.bid}, Ask: {self.ask}, Spread: {spread}")

    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")


app = TestApp()
app.connect("127.0.0.1", 7497, 10)

thread = threading.Thread(target=app.run)
thread.start()