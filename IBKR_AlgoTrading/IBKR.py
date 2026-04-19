from ibapi.client import *
from ibapi.wrapper import *
import config

class TestApp(EClient, EWrapper):
  def __init__(self):
    EClient.__init__(self, self)

  def nextValidId(self, orderId: OrderId):
    mycontract = Contract()
    mycontract.symbol = "DAX" #config.msg.get('symbol')
    mycontract.secType = "CONTFUT"    
    mycontract.exchange = config.msg.get('exchange')
    mycontract.currency = config.msg.get('currency')

    self.reqContractDetails(orderId, mycontract)

  def contractDetails(self, reqId: int, contractDetails: ContractDetails):
    print(contractDetails.contract)

    myorder = Order()
    myorder.orderId = reqId
    myorder.action = "SELL" #config.msg.get('order_action')
    myorder.tif = "DAY"
    myorder.orderType = "MKT" 
    myorder.totalQuantity = 1  #config.msg.get('order_contracts')
    myorder.eTradeOnly = False
    myorder.firmQuoteOnly = False

    self.placeOrder(myorder.orderId, contractDetails.contract, myorder)

  def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
    print(f"openOrder. orderId: {orderId}, contract: {contract}, order: {order}")

  def orderStatus(self, orderId: OrderId, status: str, filled, remaining, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
    print(f"orderId: {orderId}, status: {status}, filled: {filled}, remaining: {remaining}, avgFillPrice: {avgFillPrice}, permId: {permId}, parentId: {parentId}, lastFillPrice: {lastFillPrice}, clientId: {clientId}, whyHeld: {whyHeld}, mktCapPrice: {mktCapPrice}")

  def execDetails(self, reqId: int, contract: Contract, execution: Execution):
    print(f"reqId: {reqId}, contract: {contract}, execution: {execution}")








