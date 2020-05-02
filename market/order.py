import logging

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
    dayOrder: Order
    stopOrder: Order
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

import decimal
from decimal import Decimal
def convertToTwoDecimalsAsFloat(p):
    return float( Decimal.from_float(p).quantize(Decimal('0.01')) )

# some instruments are traded on an increment other than a penny
# in cases of less than a penny, the contract module attempts to trade
# on the penny.
# in the case of ES for example, we have to trade on the quarter
import math
def roundToTickSize(p, inc):
    if inc == 0.01:
        return p
    minD = 999999999
    parts = math.modf(p)
    intP = parts[1]
    j = int(0)
    m = None
    d = None
    while j <= int(1/inc):
        d = abs(p - intP - inc * j)
        if d < minD:
            minD = d
            m = j
        j += 1
    return m * inc + intP

def Round(p, inc):
    return convertToTwoDecimalsAsFloat( roundToTickSize(p, inc) )

def calculateProfitPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.config.profitPercent)/100.0
    else:
        return od.buyPrice + od.config.profitTarget

def calculateDayPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.config.dayPercent)/100.0
    else:
        return od.buyPrice + od.config.dayTarget

def calculateStopPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 - od.config.stopPercent)/100.0
    else:
        return od.buyPrice - od.config.stopTarget

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

    orders.buyOrder = Order()
    orders.buyOrder.transmit = False
    orders.buyOrder.action = 'BUY'
    orders.buyOrder.totalQuantity = qty
    orders.buyOrder.orderType = 'LMT'
    orders.buyOrder.lmtPrice = Round(orderDetails.buyPrice, orderDetails.wContract.priceIncrement)
    orders.buyOrder.tif = 'DAY'
    orders.buyOrder.outsideRth = orderDetails.config.buyOutsideRth

    profitPrice = calculateProfitPrice(orderDetails)
    orders.profitOrder = Order()
    orders.profitOrder.transmit = False
    orders.profitOrder.action = 'SELL'
    orders.profitOrder.totalQuantity = qty
    orders.profitOrder.orderType = 'LMT'
    orders.profitOrder.lmtPrice = Round(profitPrice, orderDetails.wContract.priceIncrement)
    orders.profitOrder.tif = 'GTC'
    orders.profitOrder.outsideRth = orderDetails.config.sellOutsideRth

    if orderDetails.config.dayOrder:
        dayPrice = calculateDayPrice(orderDetails)
        orders.dayOrder = Order()
        orders.dayOrder.transmit = False
        orders.dayOrder.action = 'SELL'
        orders.dayOrder.totalQuantity = qty
        orders.dayOrder.orderType = 'LOC'
        orders.dayOrder.lmtPrice = Round(dayPrice, orderDetails.wContract.priceIncrement)
        orders.dayOrder.tif = 'DAY'
        orders.dayOrder.outsideRth = orderDetails.config.sellOutsideRth

    orders.stopOrder = Order()
    orders.stopOrder.transmit = True
    orders.stopOrder.action = 'SELL'
    orders.stopOrder.totalQuantity = qty
    orders.stopOrder.tif = 'GTC'
    orders.stopOrder.outsideRth = orderDetails.config.sellOutsideRth
    if orderDetails.config.trail:
        orders.stopOrder.orderType = 'TRAIL'
        if orderDetails.config.stopPercent:
            orders.stopOrder.trailingPercent = orderDetails.config.stopPercent
        elif orderDetails.config.stopTarget:
            orders.stopOrder.auxPrice = orderDetails.config.stopTarget

    else:
        stopPrice = calculateStopPrice(orderDetails)
        orders.stopOrder.orderType = 'STP'
        orders.stopOrder.auxPrice = Round(stopPrice, orderDetails.wContract.priceIncrement)

    orderDetails.buyPrice = orders.buyOrder.lmtPrice # for debugging clarity
    logging.warn('created bracket orders: %s', orders)
    return orders
