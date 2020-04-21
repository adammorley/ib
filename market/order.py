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

    #buyPrice = d['third'].open + 0.5 * d['third'].barSize
    #buyPrice = bar.open + bar.barSize * 0.5 # simulating buying at market in next interval
    buyPrice = d['third'].close
    logging.info('found a potential buy point: %d, %s', buyPrice, conf.__dict__)

    #if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
    if True:
        logging.debug('valid buy point, returning')
        od = OrderDetails()
        od.buyPrice = buyPrice
        od.config = conf
        return od
    return None

from ib_insync.order import Order
class Orders:
    buyOrder: Order
    profitOrder: Order
    stopOrder: Order
    locOrder: Order
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def calculateProfitTarget(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.profitPercent)/100.0
    else:
        return od.buyPrice + od.config.profitTarget

def calculateLocTarget(od):
    if od.config.percents:
        return od.buyPrice * (100.0 + od.locPercent)/100.0
    else:
        return od.buyPrice + od.config.locTarget

def calculateStopTarget(od):
    if od.config.percents:
        return od.buyPrice * (100.0 - od.stopPercent)/100.0
    else:
        return od.buyPrice - od.config.stopTarget

# note: https://interactivebrokers.github.io/tws-api/bracket_order.html
def CreateBracketOrder(contract, orderDetails):
    orders = Orders()
    orders.buyOrder = Order(transmit=False,
                        action='BUY',
                        totalQuantity=orderDetails.config.qty,
                        orderType='LMT',
                        lmtPrice=orderDetails.buyPrice,
                        tif='DAY',
                        outsideRth=orderDetails.config.outsideRth)
    profitPrice = calculateProfitTarget(od)
    orders.profitOrder = Order(transmit=False,
                        action='SELL',
                        totalQuantity=orderDetails.config.qty,
                        orderType='LMT',
                        lmtPrice=profitPrice,
                        tif='GTC',
                        outsideRth=orderDetails.config.outsideRth)
    locPrice = calculateLocTarget(od)
    orders.locOrder = Order(transmit=False,
                        action='SELL',
                        totalQuantity=orderDetails.config.qty,
                        orderType='LOC',
                        lmtPrice=locPrice,
                        tif='DAY',
                        outsideRth=orderDetails.config.outsideRth)
    stopPrice = calculateStopTarget(od)
    if orderDetails.config.trail:
        orders.stopOrder = Order(transmit=True,
                            action='SELL',
                            totalQuantity=orderDetails.config.qty,
                            orderType='TRAIL',
                            auxPrice=stopPrice,
                            tif='GTC',
                            outsideRth=orderDetails.config.outsideRth)
    else:
        orders.stopOrder = Order(transmit=True,
                            action='SELL',
                            totalQuantity=orderDetails.config.qty,
                            orderType='STP',
                            auxPrice=stopPrice,
                            tif='GTC',
                            outsideRth=orderDetails.config.outsideRth)
    return orders
