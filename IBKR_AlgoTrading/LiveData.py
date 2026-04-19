from ibapi.client import *
from ibapi.wrapper import *
from ibapi.contract import Contract
from ibapi.order import Order
from Market_Structure import *

import pandas as pd
import threading
import time
import config
from datetime import datetime
import numpy as np


# ================== IB APP ==================

class IBApp(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        self.last_bar_time = None
        self.orderId = None
        self.in_position = False
        self.limit_price = None
        self.contract = None

    # ---------- CONNECTION ----------

    def nextValidId(self, orderId):
        print(f"✅ Connected | Next Order ID: {orderId}")
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId

    def error(self, reqId, errorCode, errorString):
        print(f"⚠️ {errorCode}: {errorString}")

    # ---------- DATA ----------

    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
        """ Callback que recibe las barras en tiempo real """
        dt = pd.to_datetime(time, unit="s")

        new_row = pd.DataFrame({
            "open": [open],
            "high": [high],
            "low": [low],
            "close": [close],
            "volume": [volume]
        }, index=[dt])

        self.df.to_csv("data.csv")

        # Añadir la nueva barra
        self.df = pd.concat([self.df, new_row])
        self.df = self.df[~self.df.index.duplicated(keep="last")]
        #self.df = self.df.tail(300)  #Mantener solo las últimas 300 barras de 5s

        # ---- RESAMPLE 3 MINUTES ----
        df_3m = self.df.resample("3min").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()

        # Solo procesar si hay suficiente data
        if len(df_3m) < 2:
            return

        # Obtener la última vela
        last_bar_time = df_3m.index[-1]

        if self.last_bar_time != last_bar_time:
            self.last_bar_time = last_bar_time
            
            # Aplicar estrategias:BOS y Risk
            df_3m = main_indicator(df_3m)
            
            zz = zigzag_with_structure(df_3m,1)
            zz = zz[zz['dir'] != zz['dir'].shift()]
            zz1= zigzag_with_structure(df_3m,40)
            zz1 = zz1[zz1['dir'] != zz1['dir'].shift()]

            df_3m = add_pivots_to_df(df_3m,zz, zz1)
            df_3m = add_risk(df_3m, config.RB)
            df_3m = add_bos(df_3m, config.buffer)

            #print(df_3m)

            # Verificar si hay señal de orden
            last = df_3m.iloc[-2]

            # ---------- SIGNAL ----------
            if self.in_position:
                return

            if df_3m["BOS_UP"].iloc[-2] and df_3m["Risk_Long"].iloc[-2]<1.5:
                print("🔥 BUY")
                self.action ="BUY"
                self.config_order(action="BUY", row = last)
                
                                  
            elif df_3m["BOS_DOWN"].iloc[-2] and df_3m["Risk_Short"].iloc[-2]<1.5:
                print("🔥 SELL")
                self.action ="SELL"
                self.config_order(action="SELL", row = last)

            # ---------- PLACE ORDER ----------
            self.place_order()
            print(f"⚡ ORDER: {self.action} @ {self.limit_price:.2f} | SL: {self.stop:.2f}")


    # ---------- CONTRACT ----------
    @staticmethod
    def create_contract()-> Contract:
        
        """ Take contrat from config file"""
        contract = Contract()
        contract = config.contract

        return contract
    
    # ---------- ORDER CONFIGURATION ----------
    def config_order(self, action, row):

        self.limit_price = row["close"]

        if action == "BUY":
            self.stop = row["ST_Long"]
            self.exit_action = "SELL"
        else:
            self.stop = row["ST_Short"]
            self.exit_action = "BUY"


    # ---------- ORDER CONFIGURATION ----------
    def place_order(self):
        
        contract = self.create_contract()
        parent_id = self.nextId()

        parent = Order()
        parent.orderId = parent_id
        parent.action = self.action #config.order["action"]
        parent.tif = "DAY"
        parent.orderType = "LMT" 
        parent.lmtPrice = self.limit_price
        parent.totalQuantity = 1 
        parent.eTradeOnly = False
        parent.firmQuoteOnly = False

        #profit_taker = Order()
        #profit_taker.orderId = parent.orderId + 1
        #profit_taker.parentId = parent.orderId
        #if parent.action == "BUY":
        #  profit_taker.action = "SELL" 
        #else: 
        #  profit_taker.action = "BUY" 
        #profit_taker.orderType = "LMT"
        #profit_taker.lmtPrice = 23000 
        #profit_taker.totalQuantity = 
        #profit_taker.transmit = False
        #profit_taker.eTradeOnly = False
        #profit_taker.firmQuoteOnly = False

        stop_loss = Order()
        stop_loss.orderId = parent_id + 1
        stop_loss.parentId = parent.orderId
        stop_loss.orderType = "STP" 
        stop_loss.action = self.exit_action
        stop_loss.auxPrice = self.stop
        stop_loss.totalQuantity = 1 
        #stop_loss.transmit = True
        stop_loss.eTradeOnly = False
        stop_loss.firmQuoteOnly = False

        self.current_stop_price = stop_loss.auxPrice
        self.stop_order_id = stop_loss.orderId
        self.current_position = parent.action
        #self.current_entry_price = parent.lmtPrice

        self.placeOrder(parent.orderId, contract, parent)
        #self.placeOrder(profit_taker.orderId, contractDetails.contract, profit_taker)
        self.placeOrder(stop_loss.orderId, contract, stop_loss)

        print(f"🚀 TRADE {self.action} | Entry: {self.limit_price} | SL: {self.stop} | Size: {1}")

        # Activar gestor automático cada X segundos
        # self.auto_manager_loop(contractDetails.contract)

    # ---------- ORDER STATUS ----------
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, *args):

        print(f"📊 Order {orderId} | {status} | Filled: {filled}")

        if status == "Filled":
            self.in_position = True
            self.entry_price = avgFillPrice

        if status in ["Cancelled", "Inactive"]:
            self.in_position = False

        if remaining == 0:
            self.in_position = False

# ================== RUN ==================

# Create and connect the application
app = IBApp()
app.connect("127.0.0.1", 7497, clientId=1)

# Execution
threading.Thread(target=app.run, daemon=True).start()
time.sleep(1)

# Create the contrat 
contract = app.create_contract()

# Request real time bars every 5 seconds
app.reqRealTimeBars(
    reqId=1,
    contract=contract,
    barSize=5,  # 5 seconds
    whatToShow="TRADES",
    useRTH=False,
    realTimeBarsOptions=[]
)

# Keep app running
while True:
    time.sleep(1)