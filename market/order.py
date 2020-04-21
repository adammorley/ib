import logging

class OrderDetails:
    buyPrice: float = 0.0
    profitPrice: float = 0.0
    stopPrice: float = 0.0

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
    if conf.trail:
        stopPrice = conf.stopPrice
    else:
        stopPrice = d['second'].close - conf.stopPrice
    buyPrice = d['third'].close
    profitPrice = d['third'].close + conf.profitPrice
    logging.info('found a potential buy point, buy: %d, stop: %d, profit: %d', buyPrice, stopPrice, profitPrice)

    #if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
    if True:
        logging.debug('valid buy point, returning')
        od = OrderDetails()
        od.stopPrice = stopPrice
        od.buyPrice = buyPrice
        od.profitPrice = profitPrice
        return od
    return None

from ib_insync.order import Order
class Orders:
    buyOrder: Order
    profitOrder: Order
    stopOrder: Order

def CreateOrders(contract, orderDetails, conf):
    orders = Orders()
    orders.buyOrder = Order(transmit=False,
                        action='BUY',
                        totalQuantity=conf.qty,
                        orderType='LMT',
                        lmtPrice=orderDetails.buyPrice,
                        tif='DAY',
                        outsideRth=True)
    order.profitOrder = Order(action='SELL',
                        totalQuantity=conf.qty,
                        orderType='LMT',
                        lmtPrice=orderDetails.profitPrice,
                        tif='GTC',
                        outsideRth=True)
    if conf.trail:
        orders.stopOrder = Order(action='SELL',
                            totalQuantity=conf.qty,
                            orderType='TRAIL',
                            auxPrice=orderDetails.stopPrice,
                            tif='GTC',
                            outsideRth=True)
    else:
        orders.stopOrder = Order(action='SELL',
                            totalQuantity=conf.qty,
                            orderType='STP',
                            auxPrice=orderDetails.stopPrice,
                            tif='GTC',
                            outsideRth=True)
    return orders
