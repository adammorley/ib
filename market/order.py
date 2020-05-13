import copy
import logging

from market import fatal

from market.contract import wContract
from market.config import Config
class OrderDetails:
    entryPrice: float = None # converts to Decimal during order creation
    config: Config
    wContract: wContract

    def __init__(self, entryPrice, config, wContract):
        self.entryPrice = entryPrice
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
    entryOrder: Order
    exitOrder: Order
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

def calculateProfitPrice(od, entryAction=None):
    if od.config.percents:
        return od.entryPrice * (100.0 + od.config.profitPercent)/100.0
    else:
        return od.entryPrice + od.config.profitTarget

def calculateDayPrice(od, entryAction=None):
    if od.config.percents:
        return od.entryPrice * (100.0 + od.config.dayPercent)/100.0
    else:
        return od.entryPrice + od.config.dayTarget

def calculateStopPrice(od, entryAction=None):
    if od.config.percents:
        return od.entryPrice * (100.0 - od.config.stopPercent)/100.0
    else:
        return od.entryPrice - od.config.stopTarget

# drops decimal, only whole units
def calculateQty(od):
    if od.config.byPrice:
        return int( od.config.dollarAmt / od.entryPrice )
    else:
        return od.config.qty

# note: https://interactivebrokers.github.io/tws-api/bracket_order.html
# order matters, see class note
def CreateBracketOrder(orderDetails, account=None):
    qty = calculateQty(orderDetails)
    orders = BracketOrder()

    orders.entryOrder = Order()
    orders.entryOrder.account = account
    orders.entryOrder.transmit = False
    orders.entryOrder.action = 'BUY'
    orders.entryOrder.totalQuantity = qty
    orders.entryOrder.orderType = 'LMT'
    orders.entryOrder.lmtPrice = Round(orderDetails.entryPrice, orderDetails.wContract.priceIncrement)
    orders.entryOrder.tif = 'DAY'

    exitPrice = calculateProfitPrice(orderDetails)
    orders.exitOrder = Order()
    orders.exitOrder.account = account
    orders.exitOrder.transmit = False
    orders.exitOrder.action = 'SELL'
    orders.exitOrder.totalQuantity = qty
    orders.exitOrder.orderType = 'LMT'
    orders.exitOrder.lmtPrice = Round(exitPrice, orderDetails.wContract.priceIncrement)
    orders.exitOrder.tif = 'GTC'
    orders.exitOrder.outsideRth = orderDetails.config.exitOutsideRth

    if orderDetails.config.dayOrder:
        dayPrice = calculateDayPrice(orderDetails)
        orders.dayOrder = Order()
        orders.dayOrder.account = account
        orders.dayOrder.transmit = False
        orders.dayOrder.action = 'SELL'
        orders.dayOrder.totalQuantity = qty
        orders.dayOrder.orderType = 'LOC'
        orders.dayOrder.lmtPrice = Round(dayPrice, orderDetails.wContract.priceIncrement)
        orders.dayOrder.tif = 'DAY'
        orders.dayOrder.outsideRth = orderDetails.config.exitOutsideRth

    orders.stopOrder = Order()
    orders.stopOrder.account = account
    orders.stopOrder.transmit = True
    orders.stopOrder.action = 'SELL'
    orders.stopOrder.totalQuantity = qty
    orders.stopOrder.tif = 'GTC'
    orders.stopOrder.outsideRth = orderDetails.config.exitOutsideRth
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

    orderDetails.entryPrice = orders.entryOrder.lmtPrice # for debugging clarity
    logging.warn('created bracket orders: %s', orders)
    return orders

# https://www.interactivebrokers.com/en/?f=%2Fen%2Fgeneral%2Feducation%2Fpdfnotes%2FWN-UnderstandingIBMargin.php%3Fib_entity%3Din
#
# Available Funds – (Equity with Loan Value less Initial margin) lets you know if funds are available to put on a new trade.
# Excess Liquidity – (Equity with Loan Value less Maintenance margin) Lets you know if you are approaching liquidations
# Buying Power – value of securities you can purchase without depositing additional funds. In cash accounts this is the settled
# cash. In a margin account, buying power is increased through the use of leverage using cash and the value of held stock as collateral.
# The amount of leverage depends upon whether you have a Reg. T Margin or Portfolio Margin account. Active traders can take advantage 
# of reduced intraday margin for securities – generally 25% of the long stock value. But keep in mind this requirement reverts to the 
# Reg T 50% of stock value to hold overnight.
from market import account
def adequateFunds(orderDetails, orders):
    qty = calculateQty(orderDetails)
    availableFunds = account.availableFunds(orderDetails.wContract.ibClient, orderDetails.config.account)
    buyingPower = account.buyingPower(orderDetails.wContract.ibClient, orderDetails.config.account)
    lhs = orderDetails.entryPrice * qty
    af_rhs = availableFunds - orderDetails.config.bufferAmt
    bp_rhs = buyingPower - orderDetails.config.bufferAmt
    os = None
    if orderDetails.wContract.contract.secType == 'FUT':
        wio = whatIfOrder(orders.entryOrder)
        os = orderDetails.wContract.ibClient.whatIfOrder(orderDetails.wContract.contract, wio)
        if not os.initMarginAfter or not isinstance(os.initMarginAfter, str):
            fatal.errorAndExit('got back invalid format: {} {} {}'.format(os, orderDetails, order))
        ima = float( os.initMarginAfter )
        lhs += ima
    if lhs < af_rhs and lhs < bp_rhs:
        logging.warn('detected adequate funds {} {} {}'.format(lhs, af_rhs, bp_rhs))
        return True
    logging.error('not enough funds: {} {} {}'.format(os, orderDetails, orders))
    return False

def whatIfOrder(order):
    wio = copy.deepcopy(order)
    wio.transmit = True
    wio.whatIf = True
    return wio
