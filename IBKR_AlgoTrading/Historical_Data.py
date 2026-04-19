from ibapi.client import *
from ibapi.wrapper import *
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
from Market_Structure import *
from Telegram import send_telegram

import time
import config
import threading
from datetime import datetime
from typing import Dict, Optional
import pandas as pd


class HistData(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.data: Dict[int, pd.DataFrame] = {}
        self.OrderId: Optional[int] = None
        self.last_bar = {}
        self.last_bar_id = {}
        self.bid = None
        self.ask = None
        self.spread = None
        self.longbracket = {"active": False}
        self.shortbracket = {"active": False}
        self.in_position_long = False
        self.in_position_short = False
        self.current_stop_price = None
        self.connected = False
        self.reconnecting = False

    def nextValidId(self, orderId: int):
        self.orderId = orderId
        self.connected = True
        send_telegram("✅ Connected/ Reconnected to IB")

        self.resubscribe()

        self.reqMarketDataType(1)

        contract = self.get_contract()

        self.market_req_id = 1000
        self.reqMktData(self.market_req_id, contract, "", False, False, [])

    def resubscribe(self):
        contract = self.get_contract()

        # Market data
        self.market_req_id = 1000
        self.reqMktData(self.market_req_id, contract, "", False, False, [])

        # Historical data stream
        self.get_historical_data(100, contract)

        send_telegram("📡 Resubscribed to data")

    
    def nextId(self):
        self.orderId += 1
        return self.orderId
    
    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")
    
    # -------------------------
    # SPREAD REQUEST
    # -------------------------
    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 1:  # BID
            self.bid = price
        elif tickType == 2:  # ASK
            self.ask = price

        # Calcular spread cuando ambos existen
        if self.bid is not None and self.ask is not None:
            self.spread = self.ask - self.bid
            print(f"Bid: {self.bid}, Ask: {self.ask}, Spread: {self.spread}")    
   
    # -------------------------
    # HISTORICAL DATA REQUEST
    # -------------------------
    def get_historical_data(self, reqId: int, contract: Contract) -> pd.DataFrame:

        self.data[reqId] = pd.DataFrame(columns=["time", "open", "high", "low", "close"])
        self.data[reqId].set_index("time", inplace=True)
        self.reqHistoricalData(
            reqId=reqId,
            contract=contract,
            endDateTime="",
            durationStr="5 D",
            barSizeSetting="3 mins",
            whatToShow="MIDPOINT",
            useRTH=0,
            formatDate=1,
            keepUpToDate=True,
            chartOptions=[],
        )
        
        #self.data[reqId+1] = pd.DataFrame(columns=["time", "open", "high", "low", "close"])
        #self.data[reqId+1].set_index("time", inplace=True)
        #self.reqHistoricalData(
        #    reqId=reqId+1,
        #    contract=contract,
        #    endDateTime="",
        #    durationStr="2 D",
        #    barSizeSetting="1 hour",
        #    whatToShow="MIDPOINT",
        #    useRTH=0,
        #    formatDate=1,
        #    keepUpToDate=True,
        #    chartOptions=[],
        #)
       
        time.sleep(5)
        return self.data[reqId]
    
        
    def historicalData(self, reqId, bar):

        # Seleccionar el dataframe correcto según el reqId
        df = self.data[reqId]

        # Convertir timestamp
        ts = pd.to_datetime(bar.date)

        # Insertar o actualizar fila
        df.loc[ts] = [bar.open, bar.high, bar.low, bar.close]

        # Asegurar tipos numéricos
        df = df[~df.index.duplicated(keep="last")]
        df = df.astype(float)
        df = df.sort_index()

        self.data[reqId] = df
        #print(reqId, bar)

    # -------------------------
    # LIVE BAR UPDATES
    # -------------------------

    def get_bar_id(ts: pd.Timestamp, timeframe_sec: int):
        return int(ts.timestamp()) // timeframe_sec

    def historicalDataUpdate(self, reqId, bar):

        ts = pd.to_datetime(bar.date)

        # ⏱ Define timeframe por reqId
        timeframe_map = {
            100: 180,   # 3 min
            101: 3600   # 1 hour
        }

        tf = timeframe_map.get(reqId, 180)

        current_bar_id = self.get_bar_id(ts, tf)

        if reqId not in self.last_bar_id:
            self.last_bar_id[reqId] = current_bar_id
            self.last_bar[reqId] = bar
            return

        prev_bar_id = self.last_bar_id[reqId]
        prev_bar = self.last_bar[reqId]

        # ✅ BAR CLOSED (ROBUST)
        if current_bar_id > prev_bar_id:

            prev_ts = pd.to_datetime(prev_bar.date)
            df = self.data[reqId]
            df.loc[prev_ts] = [
                prev_bar.open,
                prev_bar.high,
                prev_bar.low,
                prev_bar.close
            ]
            df.sort_index(inplace=True)
            self.data[reqId] = df
            print(f"✅ BAR CLOSED: {prev_bar.date}")

            self.on_bar_close(df)
        else:
            print(f"⏳ BAR IN PROGRESS: {prev_bar.date}")

        self.last_bar_id[reqId] = current_bar_id
        self.last_bar[reqId] = bar

    # -------------------------
    # STRATEGY CALLBACK
    # -------------------------

    def on_bar_close(self,df):

        # PARAMETERS COMPUTATION
        df = main_indicator(df)
            
        zz = zigzag_with_structure(df,1)
        zz = zz[zz['dir'] != zz['dir'].shift()]
        zz1= zigzag_with_structure(df,40)
        zz1 = zz1[zz1['dir'] != zz1['dir'].shift()]

        df = add_pivots_to_df(df,zz, zz1)
        df = add_risk(df, config.RB)
        df = add_bos(df, config.buffer)
        stats = Low_frequency_range(df)
        for k, v in stats.items():
            if pd.notna(v):
                print(f"{k}: {v:.2f}")
            else:
                print(f"{k}: {v}")

        # Verificar si hay señal de orden
        last = df.iloc[-1]

        self.update_stop_loss(last["ST_Long"])

        # ---------- SIGNAL ----------
        if not self.in_position_long and not self.longbracket["active"]:

            if df["BOS_UP"].iloc[-1] and df["Risk_Long"].iloc[-1]<(stats["mean_range_pct"] + stats["std_range_pct"]): # and df["dir_LF"].iloc[-1]==-1:
                print("🔥 BUY")
                self.action ="BUY"
                self.config_order(action="BUY", row = last)
                self.place_order()  

        elif  not self.in_position_short and not self.shortbracket["active"]:

            if df["BOS_DOWN"].iloc[-1] and df["Risk_Short"].iloc[-1]<(stats["mean_range_pct"] + stats["std_range_pct"]): # and df["dir_LF"].iloc[-1]==1:
                print("🔥 SELL")
                self.action ="SELL"
                self.config_order(action="SELL", row = last)
                self.place_order()
              
        df.to_csv("Market_structure.csv", index=True)

    # ---------- ORDER CONFIGURATION ----------
    def config_order(self, action, row):

        self.limit_price = row["close"]

        if action == "BUY":
            self.Risk = row["Risk_Long"]
            self.stop = row["ST_Long"]
            self.exit_action = "SELL"
            
        else:
            self.Risk = row["Risk_Short"]
            self.stop = row["ST_Short"]
            self.exit_action = "BUY"
            


    # ---------- PLACE ORDER CONFIGURATION ----------
    def place_order(self):

        if self.longbracket["active"] or self.shortbracket["active"]:
            return
        
        contract = self.get_contract()
        parent_id = self.nextId()

        parent = Order()
        parent.orderId = parent_id
        parent.action = self.action #config.order["action"]
        parent.tif = "DAY"
        parent.orderType = "MKT" 
        #parent.lmtPrice = self.limit_price
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
        self.current_order_action = parent.action

        self.placeOrder(parent.orderId, contract, parent)
        #self.placeOrder(profit_taker.orderId, contractDetails.contract, profit_taker)
        self.placeOrder(stop_loss.orderId, contract, stop_loss)

        if parent.action == "BUY": 
            self.longbracket = {
                "action": parent.action,
                "parent_id": parent.orderId,
                "sl_id": stop_loss.orderId,
                "active": True
            }
        else:
            self.shortbracket = {
                "action": parent.action,
                "parent_id": parent.orderId,
                "sl_id": stop_loss.orderId,
                "active": True
            }            

        print(f"🚀 TRADE {self.action} | Entry: {self.limit_price} | SL: {self.stop} | Size: {1}")
        msg = f"""🚀 TRADE {self.action}
        💰 Entry Price: {self.limit_price:.2f}
        📈 SL: {self.stop:.2f}
        ⚠️ Risk: {self.Risk:.2f}
        📦 Size: {1:.0f}
        """
        send_telegram(msg)

    # ---------- STOP LOSS UPDATE ----------

    def update_stop_loss(self, row):

        if not self.longbracket["active"] and not self.shortbracket["active"]:
            return
        
        contract = self.get_contract()
        new_stop_loss = Order()
        
        if self.longbracket["active"]:
            if self.current_stop_price<row["ST_Long"]:

                self.cancelOrder(self.longbracket["sl_id"])

                new_exit_action = "SELL"
                new_sl_price = row["ST_Long"]

                new_stop_loss.parentId = self.longbracket["parent_id"]
                new_sl_id = self.nextId()
                

                new_stop_loss.orderId = new_sl_id
                new_stop_loss.orderType = "STP" 
                new_stop_loss.action = new_exit_action
                new_stop_loss.auxPrice = new_sl_price
                new_stop_loss.totalQuantity = 1 
                #new_stop_loss.transmit = True
                new_stop_loss.eTradeOnly = False
                new_stop_loss.firmQuoteOnly = False

                self.placeOrder(new_sl_id, contract, new_stop_loss)
                self.longbracket["sl_id"] = new_sl_id
                self.current_stop_price = new_sl_price

                msg = f"""🚀 TRADE BUY
                📈 SL updated: {new_sl_price:.2f}
                """
                send_telegram(msg)
        
            return
    
        elif self.shortbracket["active"]:
            if self.current_stop_price>row["ST_Short"]:

                self.cancelOrder(self.shortbracket["sl_id"])

                new_exit_action = "BUY"
                new_sl_price = row["ST_Short"]

                new_stop_loss.parentId = self.shortbracket["parent_id"]
                new_sl_id = self.nextId()
                

                new_stop_loss.orderId = new_sl_id
                new_stop_loss.orderType = "STP" 
                new_stop_loss.action = new_exit_action
                new_stop_loss.auxPrice = new_sl_price
                new_stop_loss.totalQuantity = 1 
                #new_stop_loss.transmit = True
                new_stop_loss.eTradeOnly = False
                new_stop_loss.firmQuoteOnly = False

                self.placeOrder(new_sl_id, contract, new_stop_loss)
                self.shortbracket["sl_id"] = new_sl_id
                self.current_stop_price = new_sl_price

                msg = f"""🚀 TRADE SELL
                📈 SL updated: {new_sl_price:.2f}
                """
                send_telegram(msg)

            return
        
        else:
            return


    # ---------- ORDER STATUS ----------
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, *args):

        print(f"📊 Order {orderId} | {status} | Filled: {filled}")

        if status == "Filled":
            
            # ENTRY filled
            if orderId == self.longbracket["parent_id"]:
                self.in_position_long = True
                self.entry_price = avgFillPrice

            elif orderId == self.shortbracket["parent_id"]:
                self.in_position_short = True
                self.entry_price = avgFillPrice

            # STOP LOSS filled
            elif orderId == self.longbracket["sl_id"]:
                self.in_position_long = False
                self.position_long_size = 0

                self.longbracket = {
                    "action": None,
                    "parent_id": None,
                    "sl_id": None,
                    "active": False
                }

            elif orderId == self.shortbracket["sl_id"]:
                self.in_position_short = False
                self.position_short_size = 0

                self.shortbracket = {
                    "action": None,
                    "parent_id": None,
                    "sl_id": None,
                    "active": False
                } 

        if status in ["Cancelled", "Inactive"] and not self.longbracket["active"]:
            self.in_position_long = False
        elif status in ["Cancelled", "Inactive"] and not self.shortbracket["active"]:
            self.in_position_short = False
       
    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical Data Ended for {reqId}. Started at {start}, ending at {end}")
        self.cancelHistoricalData(reqId)

    def get_dataframes(self, reqId):
        df3 = self.data[reqId].sort_index()
        #df1 = self.data[reqId+1].sort_index()
        return df3 #, df1
   
    @staticmethod
    def get_contract() -> Contract:

        contract = Contract()
        contract = config.contract

        return contract
    
def run_loop(app):
    app.run()

def connection_watchdog(app):
    while True:
        if not app.isConnected():
            send_telegram("⚠️ Connection lost detected")
            app.connected = False
            app.reconnect()
        time.sleep(3)


