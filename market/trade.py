import logging
import sys

from ib_insync.order import OrderStatus

from market import rand

def PlaceBracketTrade(orders, orderDetails, ibc):
    #oca=[]
    orders.buyOrder.orderId = ibc.client.getReqId()
    for orderType, order in orders.__dict__.items():
        if orderType != 'buyOrder':
            order.orderId = ibc.client.getReqId()
            order.parentId = orders.buyOrder.orderId
            #oca.append(order)

    #ocaR = ibc.oneCancelsAll(orders=oca, ocaGroup=rand.String(), ocaType=1)
    #logging.info('oca %s, ocaR: %s', oca, ocaR)

    trades = []
    bos = None
    for orderType, order in orders.__dict__.items():
        t = ibc.placeOrder(orderDetails.wContract.contract, order)
        if orderType == 'buyOrder':
            bos = t.orderStatus
        trades.append(t)
    ibc.sleep(0)

    n = 0
    while n < 3 and bos.status != OrderStatus.Filled:
        n += 1
        ibc.sleep(1)
        if n > 1:
            logging.debug('waiting on an order fill')

    ibc.sleep(0)
    logging.debug('placed orders')
    return trades

def CheckTradeExecution(trades, orderDetails):
    ids = []
    for trade in trades:
        ids.append( str(trade.orderStatus.permId) )
        if trade.orderStatus.status == OrderStatus.Cancelled:
            logging.warn('got a canceled trade for %s doing %s %s:    Log: %s', trade.contract.symbol, trade.order.action, trade.order.orderType, trade.log)
        if trade.order.action == 'BUY' and trade.orderStatus.status != OrderStatus.Filled:
            logging.warn('BUY order on %s was not filled (outside rth?):    %s', trade.contract.symbol, trade)
        # FIXME: add thing to detect whether order flowed to get a permanent id or not

    logging.warn('entered a BUY order for %s; perm order IDs: %s',  orderDetails.wContract.symbol, ', '.join(ids))
