from ibapi.client import *
from ibapi.wrapper import *
import config

class TestApp(EClient, EWrapper):
  def __init__(self):
    EClient.__init__(self, self)

  def nextValidId(self, orderId: OrderId):

    mycontract = Contract()
    mycontract.symbol = "DAX"
    mycontract.secType = "CONTFUT"    
    mycontract.exchange = "EUREX"
    mycontract.currency = "EUR"

    self.reqContractDetails(orderId, mycontract)

  def contractDetails(self, reqId: int, contractDetails: ContractDetails):
    print(contractDetails.contract)

    parent = Order()
    parent.orderId = reqId
    parent.action = config.msg.get('order_action')
    parent.tif = "DAY"
    parent.orderType = config.msg.get('order_type')
    parent.lmtPrice = config.msg.get('order_price')
    parent.totalQuantity = config.msg.get('order_contracts')
    parent.eTradeOnly = False
    parent.firmQuoteOnly = False

    profit_taker = Order()
    profit_taker.orderId = parent.orderId + 1
    profit_taker.parentId = parent.orderId
    if parent.action == "BUY":
      profit_taker.action = "SELL" 
    else: 
      profit_taker.action = "BUY" 
    profit_taker.orderType = "LMT"
    profit_taker.lmtPrice = config.msg.get('order_profit')
    profit_taker.totalQuantity = config.msg.get('order_contracts')
    #profit_taker.transmit = False
    profit_taker.eTradeOnly = False
    profit_taker.firmQuoteOnly = False

    stop_loss = Order()
    stop_loss.orderId = parent.orderId + 2
    stop_loss.parentId = parent.orderId
    stop_loss.orderType = "STP" #config.msg.get('order_action')
    stop_loss.auxPrice = config.msg.get('order_stop')
    if parent.action == "BUY":
      stop_loss.action = "SELL"
    else:
      stop_loss.action = "BUY"
    stop_loss.totalQuantity = config.msg.get('order_contracts')
    #stop_loss.transmit = True
    stop_loss.eTradeOnly = False
    stop_loss.firmQuoteOnly = False

    self.placeOrder(parent.orderId, contractDetails.contract, parent)
    self.placeOrder(profit_taker.orderId, contractDetails.contract, profit_taker)
    self.placeOrder(stop_loss.orderId, contractDetails.contract, stop_loss)

  def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
    print(f"openOrder. orderId: {orderId}, contract: {contract}, order: {order}")

  def orderStatus(self, orderId: OrderId, status: str, filled, remaining, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
    print(f"orderId: {orderId}, status: {status}, filled: {filled}, remaining: {remaining}, avgFillPrice: {avgFillPrice}, permId: {permId}, parentId: {parentId}, lastFillPrice: {lastFillPrice}, clientId: {clientId}, whyHeld: {whyHeld}, mktCapPrice: {mktCapPrice}")

  def execDetails(self, reqId: int, contract: Contract, execution: Execution):
    print(f"reqId: {reqId}, contract: {contract}, execution: {execution}")

