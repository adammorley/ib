import logging
import sys

from market import rand

def PlaceBracketTrade(contract, orders, ibc):
    if orders.contract != contract:
        raise RuntimeError('contract mismatch')

    #oca=[]
    orders.buyOrder.orderId = ibc.client.getReqId()
    for orderType, order in orders.__dict__.items():
        if orderType != 'buyOrder':
            order.orderId = ibc.client.getReqId()
            order.parentId = orders.buyOrder.orderId
            #oca.append(order)

    #ocaR = ibc.oneCancelsAll(orders=oca, ocaGroup=rand.String(), ocaType=1)
    #logging.info('oca %s, ocaR: %s', oca, ocaR)

    trades = dict()
    for orderType, order in orders.__dict__.items():
        trades[orderType] = ibc.placeOrder(contract, order)
    ibc.sleep(0)

    n = 0
    while n < 3 and trades['buyOrder'].orderStatus.status != 'Filled':
        n += 1
        ibc.sleep(1)
        if n > 1:
            logging.debug('waiting on an order fill')

    ibc.sleep(0)
    logging.debug('placed orders')
    return trades
