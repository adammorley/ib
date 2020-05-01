import logging
import math

from market.contract import wContract
from market.config import Config
class OrderDetails:
    buyPrice: float = None # converts to Decimal during order creation
    config: Config
    wContract: wContract

    def __init__(self, buyPrice, config, wContract):
        self.buyPrice = buyPrice
        self.config = config
        self.wContract = wContract

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

import decimal
from decimal import Decimal
dContext = decimal.getcontext()
dContext.prec = 4 # LETPs use four!  wtf
dContext.traps[decimal.FloatOperation] = True
decimal.setcontext(dContext)
def roundToTickSize(wc, price):
    minTick = Decimal.from_float(wc.details.minTick)

    if minTick == Decimal.from_float(0.01):
        if len(wc.marketRule) > 1 or Decimal.from_float(wc.marketRule[0].increment) != minTick:
            raise RuntimeError('not implemented')

    dContext.prec = 2 # but we use pennies, unfortunately
    decimal.setcontext(dContext)
    return Decimal.from_float(price)

dContext.prec = 2
decimal.setcontext(dContext)
def calculateProfitPrice(od):
    if od.config.percents:
        return od.buyPrice * Decimal.from_float( (100.0 + od.config.profitPercent)/100.0 )
    else:
        return od.buyPrice + Decimal.from_float(od.config.profitTarget)

def calculateLocPrice(od):
    if od.config.percents:
        return od.buyPrice * Decimal.from_float( (100.0 + od.config.locPercent)/100.0 )
    else:
        return od.buyPrice + Decimal.from_float(od.config.locTarget)

def calculateStopPrice(od):
    if od.config.percents:
        return od.buyPrice * Decimal.from_float( (100.0 - od.config.stopPercent)/100.0 )
    else:
        return od.buyPrice - Decimal.from_float(od.config.stopTarget)

# drops decimal, only whole units
def calculateQty(od):
    if od.config.byPrice:
        return int( od.config.dollarAmt / od.buyPrice )
    else:
        return od.config.qty

# note: https://interactivebrokers.github.io/tws-api/bracket_order.html
# order matters, see class note
def CreateBracketOrder(orderDetails):
    qty = calculateQty(orderDetails)
    orders = BracketOrder()

    orderDetails.buyPrice = roundToTickSize(orderDetails.wContract, orderDetails.buyPrice)

    orders.buyOrder = Order()
    orders.buyOrder.transmit = False
    orders.buyOrder.action = 'BUY'
    orders.buyOrder.totalQuantity = qty
    orders.buyOrder.orderType = 'LMT'
    orders.buyOrder.lmtPrice = float( orderDetails.buyPrice )
    orders.buyOrder.tif = 'DAY'
    orders.buyOrder.outsideRth = orderDetails.config.buyOutsideRth

    profitPrice = calculateProfitPrice(orderDetails)
    orders.profitOrder = Order()
    orders.profitOrder.transmit = False
    orders.profitOrder.action = 'SELL'
    orders.profitOrder.totalQuantity = qty
    orders.profitOrder.orderType = 'LMT'
    orders.profitOrder.lmtPrice = float( profitPrice )
    orders.profitOrder.tif = 'GTC'
    orders.profitOrder.outsideRth = orderDetails.config.sellOutsideRth

    if orderDetails.config.locOrder:
        locPrice = calculateLocPrice(orderDetails)
        orders.locOrder = Order()
        orders.locOrder.transmit = False
        orders.locOrder.action = 'SELL'
        orders.locOrder.totalQuantity = qty
        orders.locOrder.orderType = 'LOC'
        orders.locOrder.lmtPrice = float( locPrice )
        orders.locOrder.tif = 'DAY'
        orders.locOrder.outsideRth = orderDetails.config.sellOutsideRth

    orders.stopOrder = Order()
    orders.stopOrder.transmit = True
    orders.stopOrder.action = 'SELL'
    orders.stopOrder.totalQuantity = qty
    orders.stopOrder.tif = 'GTC'
    orders.stopOrder.outsideRth = orderDetails.config.sellOutsideRth
    if orderDetails.config.trail:
        orders.stopOrder.orderType = 'TRAIL'
        orders.stopOrder.trailingPercent = orderDetails.config.stopPercent
    else:
        stopPrice = calculateStopPrice(orderDetails)
        orders.stopOrder.orderType = 'STP'
        orders.stopOrder.auxPrice = float( stopPrice )

    logging.warn('created bracket orders: %s', orders)
    return orders
