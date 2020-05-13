import logging
import sys

from ib_insync.order import OrderStatus

from market import rand

def PlaceBracketTrade(orders, orderDetails):
    #oca=[]
    orders.buyOrder.orderId = orderDetails.wContract.ibClient.client.getReqId()
    for orderType, order in orders.__dict__.items():
        if orderType != 'buyOrder':
            order.orderId = orderDetails.wContract.ibClient.client.getReqId()
            order.parentId = orders.buyOrder.orderId
            #oca.append(order)

    #ocaR = ibc.oneCancelsAll(orders=oca, ocaGroup=rand.String(), ocaType=1)
    #logging.info('oca %s, ocaR: %s', oca, ocaR)

    trades = []
    bos = None
    for orderType, order in orders.__dict__.items():
        t = orderDetails.wContract.ibClient.placeOrder(orderDetails.wContract.contract, order)
        if orderType == 'buyOrder':
            bos = t.orderStatus
        trades.append(t)
    orderDetails.wContract.ibClient.sleep(0)

    n = 0
    while n < 3 and bos.status != OrderStatus.Filled:
        n += 1
        orderDetails.wContract.ibClient.sleep(1)
        if n > 1:
            logging.debug('waiting on an order fill')

    orderDetails.wContract.ibClient.sleep(0)

    stop = None
    if orderDetails.config.trail:
        stop = orders.stopOrder.trailingPercent
    else:
        stop = orders.stopOrder.auxPrice
    orderDetails.wContract.ibClient.sleep(0)
    return trades

def CheckTradeExecution(trades, orderDetails):
    ids = []
    out = ''
    for trade in trades:
        price = trade.order.lmtPrice if trade.order.lmtPrice > 0.0 else trade.order.auxPrice
        logging.warn('placed a trade, action: {}, type: {}, id: {}, permId: {}, price: {}, avgFillPrice: {}, qty: {}, tif: {}'.format(trade.order.action, trade.order.orderType, trade.order.orderId, trade.orderStatus.permId, price, trade.orderStatus.avgFillPrice, trade.order.totalQuantity, trade.order.tif))
        if trade.orderStatus.status == OrderStatus.Cancelled:
            logging.error('got a canceled trade for %s doing %s %s:    Log: %s', trade.contract.symbol, trade.order.action, trade.order.orderType, trade.log)
