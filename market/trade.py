import logging

from market import rand

def PlaceTrade(contract, orders, ibc):
    # do some annotation with the client
    for order in orders:
        order.orderId = ibc.client.getReqId()
    for order in [orders.profitOrder, orders.stopOrder]:
        order.parentId = orders.buyOrder.orderId

    oneCancelsAll = ibc.oneCancelsAll(
                        [orders.profitOrder, orders.stopOrder],
                        ocaType=1,
                        ocaGroup=rand.String())

    trades = dict()
    trades[orders.buyOrder] = ibc.placeOrder(contract, order)
    ibc.sleep(0)
    while n < 10 and trades[orders.buyOrder].orderStatus.status != 'Filled':
        n += 1
        ibc.sleep(1)
        logging.info('waiting on an order fill')

    for order in [orders.profitOrder, orders.stopOrder]:
        trades[order] = ibc.placeOrder(contract, order)

    ibc.sleep(0)
    logging.info('placed orders')
    return trades
