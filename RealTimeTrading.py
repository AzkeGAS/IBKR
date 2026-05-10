import config
import threading
import time
import pandas as pd
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from Market_Signals import SignalEngine
from Telegram import send_telegram

class IBTradingBot(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        # ---- DATAFRAME ----
        self.df_up = pd.DataFrame(columns=['time','open','high','low','close','volume'])
        self.df = pd.DataFrame(columns=['time','open','high','low','close','volume'])
        self.current_bar_time = None

        # ---- config ----
        self.signal_engine = SignalEngine()

        # ---- state ----
        self.current_position = 0
        self.open_orders = {}
        self.nextOrderId = None
 
        self.parent_order_id = None
        self.long_parent_order_id = None
        self.short_parent_order_id = None
        self.long_stop_order_id = None
        self.short_stop_order_id = None
        self.stop_price = None
        self.action = None

        self.current_positions = {}
        
        self.current_position_side = None
        self.recovered = False

        self.active_long = False
        self.active_short = False
        self.active_long_stop = None
        self.active_short_stop = None

        self.bracket = {}

        self.buffer = config.buffer
        self.RB = config.RB

    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        print("Connected. NextOrderId:", orderId)

        self.request_history()
        self.reqPositions()
        self.reqOpenOrders()
        self.reqContractDetails(2, self.get_contract())

        send_telegram("✅ Connected/ Reconnected to IB")

    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")

    @staticmethod
    def get_contract() -> Contract:

        contract = Contract()
        contract = config.contract

        return contract
    
    def contractDetails(self, reqId, contractDetails):
        self.tick_size = contractDetails.minTick

    def request_history(self):

        self.reqHistoricalData(
            reqId=1,
            contract=self.get_contract(),
            endDateTime="",
            durationStr="5 D",
            barSizeSetting="3 mins",
            whatToShow="MIDPOINT",
            useRTH=False,
            formatDate=1,
            keepUpToDate=True,
            chartOptions=[]
        )

    def historicalData(self, reqId, bar):
        self.append_bar(bar)

    def historicalDataUpdate(self, reqId, bar):
        self.on_bar_update(bar)

    def append_bar(self, bar):
        new_row = {
            "time": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        }
        
        
        self.df_up.loc[len(self.df_up)] = new_row

        self.df_up.to_csv("DAX_Update_Data.csv", index=True)

        df_hist = pd.read_csv("DAX_Raw_Data.csv", index_col=0)

        df_merge = pd.concat([df_hist, self.df_up], ignore_index=True).drop_duplicates(subset='time', keep='last').sort_values(by='time').reset_index(drop=True)

        #self.df.loc[len(self.df)] = new_row
        df_merge.to_csv("DAX_Full_Data.csv", index=True)

        self.df = df_merge

        #self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        #self.df = self.signal_engine.generate_signals(self.df, self.buffer, self.RB)
        #print(self.df.tail(5))
        #self.df.to_csv("DAX_Signal_Data.csv", index=True)

        # ---------------- BAR CLOSE LOGIC ----------------
    def on_bar_update(self, bar):
        if self.current_bar_time != bar.date:
            if self.current_bar_time is not None:
                self.on_bar_close()

            self.current_bar_time = bar.date
        self.append_bar(bar)

    def on_bar_close(self):
        
        self.df = self.signal_engine.Real_time_signals(self.df, self.buffer, self.RB)

        self.df.to_csv("DAX_Real_Time_Signal_Data.csv", index=True)

        last = self.df.iloc[-1]

        self.management_signal(signal=last['confirmed_signal'], row=last)

        print(f"✅ BAR CLOSED: {self.current_bar_time} |Direction: {last['dir_tf']} |Long: {last['ST_Long']:.0f}-{last['KO_Long']:.0f} |Short: {last['ST_Short']:.0f}-{last['KO_Short']:.0f} ")
        print(f"Active Long: {self.active_long}-{self.active_long_stop} | Active Short: {self.active_short}-{self.active_short_stop}")
        print(f"Tentative Trade: {last['Tentative']} | RRR: {last['Risk-Reward-Ratio']:.2f} | P50 KO level: {last['P50_stop_loss']:.0f} | Tradable: {last['Tradable']} | Signal: {last['confirmed_signal']}")

# ---------------- EXECUTION ----------------
    def management_signal(self, signal, row):

        # Skip if signal is NaN/None
        if pd.isna(signal):
            return

        # Order parameters
        price = row["close"]
        #lmtprice = self.df['H'].dropna.iloc[-1] if signal == "LONG" else self.df['L'].dropna.iloc[-1]
        Tradable = row ['Tradable']
        stop_price = row["ST_Long"] if signal == " GO LONG" else row["ST_Short"]
        profit_Dist = (price-stop_price)*row['Risk-Reward-Ratio']
        RRR = row['Risk-Reward-Ratio']
        qty = 2

        # Place order if signal is confirmed

        if signal == "GO LONG" and self.active_long == False:
            self.place_bracket("BUY", qty, price, stop_price, RRR)

        elif signal == "GO SHORT" and self.active_short == False:
            self.place_bracket("SELL", qty, price, stop_price, RRR)

        if self.active_long == False or self.active_short == False:
            return

        # Update stop every bar

        if self.active_long == True:
            if row["ST_Long"] > self.active_long_stop:
                self.update_stop(row["ST_Long"], "SELL")
                self.active_long_stop = row["ST_Long"]

        elif self.active_short == True:
            if row["ST_Short"] < self.active_short_stop:
                self.update_stop(row["ST_Short"], "BUY")
                self.active_short_stop = row["ST_Short"]

    def place_bracket(self, action, qty, entry, stop, RRR):
        parent_id = self.nextOrderId
        self.nextOrderId += 2

        contract = self.get_contract()

        parent = Order()
        parent.orderId = parent_id
        parent.action = action
        parent.orderType = "MKT"
        parent.totalQuantity = qty
        #parent.lmtPrice = entry
        parent.transmit = False
        parent.eTradeOnly = False
        parent.firmQuoteOnly = False

        stop_order = Order()
        stop_order.orderId = parent_id + 1
        stop_order.action = "SELL" if action == "BUY" else "BUY"
        stop_order.orderType = "STP"
        stop_order.auxPrice = stop
        stop_order.totalQuantity = qty
        stop_order.parentId = parent_id
        stop_order.transmit = True
        stop_order.eTradeOnly = False
        stop_order.firmQuoteOnly = False

        self.placeOrder(parent.orderId, contract, parent)
        self.placeOrder(stop_order.orderId, contract, stop_order)

        #self.stop_order_id = stop_order.orderId
        self.stop_price = stop_order.auxPrice
        self.current_position_side = "LONG" if action == "BUY" else "SHORT"

        self.bracket[action]= {
            "parent_id": parent.orderId,
            "position_side": self.current_position_side,
            "entry": parent.lmtPrice,
            "stop_id": stop_order.orderId,
            "stop": stop_order.auxPrice,
            "RRR": RRR
        }

        if action == "BUY":
            self.active_long = True
            self.entry_price_long = entry
            self.active_long_stop = stop
            self.long_target_price = entry + (entry-stop)*RRR 
            self.long_parent_order_id = parent.orderId
            self.long_stop_order_id = stop_order.orderId
        else:
            self.active_short = True
            self.entry_price_short = entry
            self.active_short_stop = stop
            self.short_target_price = entry - (stop-entry)*RRR
            self.short_parent_order_id = parent.orderId
            self.short_stop_order_id = stop_order.orderId

        print(f"🚀 TRADE {action} | Entry: {entry} | SL: {stop} | Size: {qty}")
        msg = f"""🚀 {action} ORDER EXECUTED

        💰 Entry Price: {entry:.2f}
        🛑 SL: {stop:.2f}
        ⚖️ RRR: {RRR:.2f}% - {self.df['Risk_max'].iloc[-1]:.2f}%
        📦 Size: {qty:.0f}
        """

        send_telegram(msg)
  
  
    def update_stop(self, new_stop, action):
    
        contract = self.get_contract()

        new_order = Order()
        new_order.orderId = self.long_stop_order_id if action == "SELL" else self.short_stop_order_id
        new_order.action = action
        new_order.orderType = "STP"
        new_order.auxPrice = new_stop
        new_order.totalQuantity = 2

        new_order.eTradeOnly = False
        new_order.firmQuoteOnly = False
        
        # Place new stop order
        self.placeOrder(new_order.orderId, contract, new_order)

        if action == "BUY":
            self.active_long = True
            self.active_long_stop = new_stop
            self.stop_long_order_id = new_order.orderId
        else:
            self.active_short = True
            self.active_short_stop = new_stop
            self.stop_short_order_id = new_order.orderId

        send_telegram(f"🔄 Long Stop Loss updated → {new_stop:.2f}") if self.active_long == True else send_telegram(f"🔄 Short Stop Loss updated → {new_stop:.2f}") 

    # --------------------------------------------------
    # BREAK EVEN
    # --------------------------------------------------
    def break_even_update(self, price):

        if self.active_long == True:
            if price >= self.long_target_price:
                self.update_stop(self.entry_price_long, "SELL")
                self.active_long_stop = self.entry_price_long

        elif self.active_short == True:
            if price <= self.short_target_price:
                self.update_stop(self.entry_price_short, "BUY")
                self.active_short_stop = self.entry_price_short

    # --------------------------------------------------
    # TICK DATA
    # --------------------------------------------------
    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 4:  # LAST
            if self.active_long or self.active_short:
                self.break_even_update(price)

    # ---------------- POSITION ----------------
    def position(self, account, contract, position, avgCost):

        self.current_position = position
        key = (contract.symbol, contract.secType, contract.currency)

        self.current_positions[key] = {
            "position": position,
            "avgCost": avgCost
        }

    def positionEnd(self):
        print("Positions updated")

        my_contract = self.get_contract()
        key = (my_contract.symbol, my_contract.secType, my_contract.currency)

        if key in self.current_positions:
            pos = self.current_positions[key]["position"]
            self.current_position = pos

            if pos > 0:
                self.current_position_side = "LONG"
            elif pos < 0:
                self.current_position_side = "SHORT"
            else:
                self.current_position_side = None

            print(f"📊 Position: {pos} ({self.current_position_side})")
        else:
            self.current_position = 0
            self.current_position_side = None

        #self.current_positions_loaded = True
        self.check_recovery_done()

    def openOrder(self, orderId, contract, order, orderState):
        
        self.open_orders[orderId] = {
            "status": orderState.status,
            "type": order.orderType,    # MKT / LMT / STP
            "action": order.action,     # BUY / SELL
            "parentId": order.parentId,
            "orderId": orderId,
            "price": order.lmtPrice if order.orderType == "LMT" else order.auxPrice
        }
        print(f"📬 OpenOrder: {self.open_orders[orderId]}")

        # Detect parent
        if order.orderType == "LMT":
            self.parent_order_id = orderId
            self.action = order.action
            
        # Detect stop
        if order.orderType == "STP":
            self.stop_order_id = orderId
            self.action = order.action
            
            if self.action == "SELL":
                self.active_long = True
                self.active_long_stop = order.auxPrice
            elif self.action == "BUY":
                self.active_short = True
                self.active_long = False
                self.active_short_stop = order.auxPrice

    def openOrderEnd(self):
        self.orders_loaded = True
        self.check_recovery_done()
        print("✅ Orders recovered")

    def check_recovery_done(self):
        if getattr(self, "orders_loaded", False) and getattr(self, "positions_loaded", False):
            self.recovered = True
            print("🟢 FULL STATE RECOVERED")

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

            app.connect("127.0.0.1", 7497, clientId=10)

            #threading.Thread(target=app.run, daemon=True).start()
        time.sleep(1)

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