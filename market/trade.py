import logging
import sys

from market import rand

def PlaceBracketTrade(contract, orders, ibc):
    for order in orders:
        order.orderId = ibc.client.getReqId()
    for order in [orders.profitOrder, orders.locOrder, orders.stopOrder]:
        order.parentId = orders.buyOrder.orderId

    # the order matters here because of the transmit flat
    #   see https://interactivebrokers.github.io/tws-api/bracket_order.html
    trades = dict()
    for order in [orders.buyOrder, orders.profitOrder, orders.locOrder, orders.stopOrder]:
        trades[order] = ibc.placeOrder(contract, order)
    ibc.sleep(0)

    n = 0
    while n < 10 and trades[orders.buyOrder].orderStatus.status != 'Filled':
        n += 1
        ibc.sleep(1)
        logging.info('waiting on an order fill')

    ibc.sleep(0)
    logging.info('placed orders')
    return trades
