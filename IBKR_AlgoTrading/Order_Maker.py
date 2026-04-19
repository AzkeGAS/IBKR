from ibapi.client import *
from ibapi.wrapper import *
import config
import time
import pandas as pd
import numpy as np
import talib as ta
from LiveData import IBApp

class Market_Order(EClient, EWrapper):
  def __init__(self):
    EClient.__init__(self, self)

  def nextValidId(self, orderId: OrderId):

    mycontract = Contract()
    mycontract = config.contract

    self.reqContractDetails(orderId, mycontract)

  def contractDetails(self, reqId: int, contractDetails: ContractDetails):
    print(contractDetails.contract)

    parent = Order()
    parent.orderId = reqId
    parent.action = IBApp.action #config.order["action"]
    parent.tif = "DAY"
    parent.orderType = "LMT" 
    parent.lmtPrice = IBApp.limit_price
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
    stop_loss.orderId = parent.orderId + 1
    stop_loss.parentId = parent.orderId
    stop_loss.orderType = "STP" 
    stop_loss.action = IBApp.exit_action
    stop_loss.auxPrice = IBApp.stop
    stop_loss.totalQuantity = 1 
    #stop_loss.transmit = True
    stop_loss.eTradeOnly = False
    stop_loss.firmQuoteOnly = False

    self.current_stop_price = stop_loss.auxPrice
    self.stop_order_id = stop_loss.orderId
    self.current_position = parent.action
    #self.current_entry_price = parent.lmtPrice

    self.placeOrder(parent.orderId, contractDetails.contract, parent)
    #self.placeOrder(profit_taker.orderId, contractDetails.contract, profit_taker)
    self.placeOrder(stop_loss.orderId, contractDetails.contract, stop_loss)

    # Activar gestor automático cada X segundos
    self.auto_manager_loop(contractDetails.contract)

  def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
    print(f"openOrder. orderId: {orderId}, contract: {contract}, order: {order}")

  def orderStatus(self, orderId: OrderId, status: str, filled, remaining, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
    print(f"orderId: {orderId}, status: {status}, filled: {filled}, remaining: {remaining}, avgFillPrice: {avgFillPrice}, permId: {permId}, parentId: {parentId}, lastFillPrice: {lastFillPrice}, clientId: {clientId}, whyHeld: {whyHeld}, mktCapPrice: {mktCapPrice}")

    if status == "Cancelled":
      self.cancelled_orders.add(orderId)
    
  def execDetails(self, reqId: int, contract: Contract, execution: Execution):
    print(f"reqId: {reqId}, contract: {contract}, execution: {execution}")

  def auto_manager_loop(self, contract):
    while True:
      time.sleep(1)
      self.Stop_Loss_Manager(contract)

  
  def wait_for_cancellation(self, order_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
      if order_id in self.cancelled_orders:
        return True
      time.sleep(0.1)
    return False
  
  def Stop_Loss_Manager (self, contract):
    
    if self.current_position == "BUY":
      new_stop_price = config.signal["ST_UP"]
    else:
      new_stop_price = config.signal["ST_DOWN"]


    if new_stop_price <= self.current_stop_price and self.current_position == "BUY":
      return  # no mover
    if new_stop_price >= self.current_stop_price and self.current_position == "SELL":
      return

    # Cancelar stop antiguo
    self.cancelOrder(self.stop_order_id)

    # Crear nuevo stop
    new_id = self.stop_order_id + 1  # nuevo ID seguro
    new_stop = Order()
    new_stop.orderId = new_id
    if self.current_position == "BUY":
      new_stop.action = "SELL"
    else:
      new_stop.action = "BUY"
    new_stop.orderType = "STP"
    new_stop.auxPrice = new_stop_price
    new_stop.totalQuantity = 1

    new_stop.transmit = True

    self.placeOrder(new_id, contract, new_stop)

    # Actualizar estado interno
    self.current_stop_price = new_stop_price
    self.stop_order_id = new_id

Mkt = Market_Order()
Mkt.connect("127.0.0.1", 7497, 100)
Mkt.run()

