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
    logging.warn('submitted BUY @ {}, id: {}, qty: {}, tif: {}, LMT @ {}, id: {}, qty: {}, tif: {}, STP/TRAIL @ {}, id: {}, qty: {}, tif: {}'.format(orders.buyOrder.lmtPrice, orders.buyOrder.orderId, orders.buyOrder.totalQuantity, orders.buyOrder.tif, orders.profitOrder.lmtPrice, orders.profitOrder.orderId, orders.profitOrder.totalQuantity, orders.profitOrder.tif, stop, orders.stopOrder.orderId, orders.stopOrder.totalQuantity, orders.stopOrder.tif))
    orderDetails.wContract.ibClient.sleep(0)
    return trades

def CheckTradeExecution(trades, orderDetails):
    ids = []
    out = ''
    for trade in trades:
        price = trade.order.lmtPrice if trade.order.lmtPrice > 0.0 else trade.order.auxPrice
        out += 'found a {} order, type: {}, id: {}, permID: {}, price: {}, qty: {}, tif: {}, avgFillPrice: {};'.format(trade.order.action, trade.order.orderType, trade.order.orderId, trade.orderStatus.permId, price, trade.order.totalQuantity, trade.order.tif, trade.orderStatus.avgFillPrice)
        if trade.orderStatus.status == OrderStatus.Cancelled:
            logging.error('got a canceled trade for %s doing %s %s:    Log: %s', trade.contract.symbol, trade.order.action, trade.order.orderType, trade.log)
        if trade.order.action == 'BUY' and trade.orderStatus.status != OrderStatus.Filled:
            logging.error('BUY order on %s was not filled (outside rth?):    %s', trade.contract.symbol, trade)
        # FIXME: add thing to detect whether order flowed to get a permanent id or not

    logging.warn('entered some orders for {}: {}'.format(orderDetails.wContract.localSymbol, out))
