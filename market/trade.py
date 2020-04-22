import logging
import sys

from market import rand

def PlaceBracketTrade(contract, orders, ibc):
    for orderType, order in orders.__dict__.items():
        order.orderId = ibc.client.getReqId()
        if orderType == 'buyOrder':
            continue
        else:
            order.parentId = orders.buyOrder.orderId

    trades = dict()
    for orderType, order in orders.__dict__.items():
        trades[orderType] = ibc.placeOrder(contract, order)
    ibc.sleep(0)

    n = 0
    while n < 10 and trades['buyOrder'].orderStatus.status != 'Filled':
        n += 1
        ibc.sleep(1)
        logging.info('waiting on an order fill')

    ibc.sleep(0)
    logging.info('placed orders')
    return trades
