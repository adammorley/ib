import logging

from ib_insync.order import Contract
from market.config import Config
class OrderDetails:
    buyPrice: float = None
    config: Config
    contract: Contract

    def __init__(self, buyPrice, config, contract):
        self.buyPrice = buyPrice
        self.config = config
        self.contract = contract

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

from ib_insync.order import Order
# order of attributes matters so callers can iterate
# sucks but need transmit=False on the first elements
class BracketOrder:
    buyOrder: Order
    profitOrder: Order
    locOrder: Order
    stopOrder: Order
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def calculateProfitPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.config.profitPercent)/100.0
    else:
        return od.buyPrice + od.config.profitTarget

def calculateLocPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.config.locPercent)/100.0
    else:
        return od.buyPrice + od.config.locTarget

def calculateStopPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 - od.config.stopPercent)/100.0
    else:
        return od.buyPrice - od.config.stopTarget

# drops decimal, only whole units
def calculateQty(od):
    if od.config.byPrice:
        od.config.qty = int( od.config.dollarAmt / od.buyPrice )

# note: https://interactivebrokers.github.io/tws-api/bracket_order.html
# order matters, see class note
def CreateBracketOrder(orderDetails):
    calculateQty(orderDetails)

    orders = BracketOrder()

    orders.buyOrder = Order()
    orders.buyOrder.transmit = False
    orders.buyOrder.action = 'BUY'
    orders.buyOrder.totalQuantity = orderDetails.config.qty
    orders.buyOrder.orderType = 'LMT'
    orders.buyOrder.lmtPrice = orderDetails.buyPrice
    orders.buyOrder.tif = 'DAY'
    orders.buyOrder.outsideRth = orderDetails.config.buyOutsideRth

    profitPrice = calculateProfitPrice(orderDetails)
    orders.profitOrder = Order()
    orders.profitOrder.transmit = False
    orders.profitOrder.action = 'SELL'
    orders.profitOrder.totalQuantity = orderDetails.config.qty
    orders.profitOrder.orderType = 'LMT'
    orders.profitOrder.lmtPrice = profitPrice
    orders.profitOrder.tif = 'GTC'
    orders.profitOrder.outsideRth = orderDetails.config.sellOutsideRth

    locPrice = calculateLocPrice(orderDetails)
    orders.locOrder = Order()
    orders.locOrder.transmit = False
    orders.locOrder.action = 'SELL'
    orders.locOrder.totalQuantity = orderDetails.config.qty
    orders.locOrder.orderType = 'LOC'
    orders.locOrder.lmtPrice = locPrice
    orders.locOrder.tif = 'DAY'
    orders.locOrder.outsideRth = orderDetails.config.sellOutsideRth

    orders.stopOrder = Order()
    orders.stopOrder.transmit = True
    orders.stopOrder.action = 'SELL'
    orders.stopOrder.totalQuantity = orderDetails.config.qty
    orders.stopOrder.tif = 'GTC'
    orders.stopOrder.outsideRth = orderDetails.config.sellOutsideRth
    if orderDetails.config.trail:
        orders.stopOrder.orderType = 'TRAIL'
        orders.stopOrder.trailingPercent = orderDetails.config.stopPercent
    else:
        stopPrice = calculateStopPrice(od)
        orders.stopOrder.orderType = 'STP'
        orders.stopOrder.auxPrice = stopPrice

    return orders
