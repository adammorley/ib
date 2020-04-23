import logging

from market.config import Config
class OrderDetails:
    buyPrice: float = 0.0
    config: Config
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def Analyze(d, conf):
    if d['first'].color == 'X' or d['second'].color == 'X' or d['third'].color == 'X':
        logging.debug('got a partial bar')
        return None
    if not d['first'].color == 'G':
        return None
    if not d['second'].color == 'R':
        return None
    if not d['third'].color == 'G':
        return None
    if not d['second'].barSize < 0.2 * d['first'].barSize:
        return None
    if not d['second'].barSize < 0.5 * d['third'].barSize:
        return None
    if not d['third'].barSize > d['second'].barSize:
        return None

    buyPrice = d['third'].close
    if buyPrice != buyPrice:
        # likely NaN, data issue
        logging.debug('got an NaN, aborting')
        return None
    logging.debug('found a potential buy point: %d, %s', buyPrice, conf.__dict__)
    logging.debug('valid buy point, returning')
    od = OrderDetails()
    od.buyPrice = buyPrice
    od.config = conf
    return od

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
        return od.buyPrice * (100.0 + od.profitPercent)/100.0
    else:
        return od.buyPrice + od.config.profitTarget

def calculateLocPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.locPercent)/100.0
    else:
        return od.buyPrice + od.config.locTarget

def calculateStopPrice(od):
    if od.config.percents:
        return od.buyPrice * (100.0 - od.stopPercent)/100.0
    else:
        return od.buyPrice - od.config.stopTarget

# note: https://interactivebrokers.github.io/tws-api/bracket_order.html
# order matters, see class note
def CreateBracketOrder(contract, orderDetails):
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

    stopPrice = calculateStopPrice(orderDetails)
    orders.stopOrder = Order()
    orders.stopOrder.transmit = True
    orders.stopOrder.action = 'SELL'
    orders.stopOrder.totalQuantity = orderDetails.config.qty
    orders.stopOrder.auxPrice = stopPrice
    orders.stopOrder.tif = 'GTC'
    orders.stopOrder.outsideRth = orderDetails.config.sellOutsideRth
    if orderDetails.config.trail:
        orders.stopOrder.orderType = 'TRAIL'
    else:
        orders.stopOrder.orderType = 'STP'
    return orders
