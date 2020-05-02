import logging

from market import bars
from market import order

def anotateBars(histBars):
    newBars = []
    for i in range(0, len(histBars)):
        newBars.append(makeBar(histBars[i]))
        newBars[i].anotate()
    logging.info('got %d bars', len(newBars))
    return newBars

def makeBar(histBar):
    bar = bars.Bar(0)
    bar.open = histBar.open
    bar.close = histBar.close
    bar.high = histBar.high
    bar.low = histBar.low
    return bar

def getNextBar(newBars, index):
    return newBars[index]

# only used to check the third bar for if the order bought/sold in the third bar during "blur"
# eg this is an unknown because we aren't analyzing by-second data
def checkTradeExecution(bar, orders):
    if orders.buyOrder.lmtPrice <= bar.high and orders.stopOrder.auxPrice >= bar.low:
        return None, (orders.stopOrder.auxPrice - orders.buyOrder.lmtPrice)
    else:
        return orders, None

# check all the open positions
def checkPositions(wc, positions, conf, dataStore, dataStream, index, totals):
    for position in positions:
        closed, amount = None, None
        if conf.detector == 'threeBarPattern':
            closed, amount = checkPosition(dataStore.third, position)
        elif conf.detector == 'emaCrossover':
            closed, amount = checkPosition(dataStream[index], position)

        if closed:
            logging.warn('closed a position: {} {} {} {} {}'.format(amount, closed, position, dataStore, dataStream[index]))
            totals['gl'] += amount
            if totals['tf'] > totals['mf']:
                totals['mf'] = totals['tf']
            totals['tf'] -= position.buyOrder.lmtPrice * position.buyOrder.totalQuantity
            positions.remove(position)
        elif not closed and position.stopOrder.orderType == 'TRAIL':
            closePrice = dataStream[index].close
            if closePrice > position.buyOrder.lmtPrice:
                if orders.stopOrder.trailingPercent:
                    position.stopOrder.auxPrice = order.Round( closePrice * (100.0 - position.stopOrder.trailingPercent)/100.0, wc.priceIncrement)
                elif conf.stopTarget:
                    position.stopOrder.auxPrice = order.Round( closePrice - conf.stopTarget)
        #else position stays, no changes
    return positions, totals

# check if a "position" (represented by a fictitious order) changed in the bar
# returns orderDetails and amount
def checkPosition(bar, position):
    amount, executed = checkStopProfit(position, bar)
    if executed == False:
        # order became a position, say so
        return False, None
    elif executed == True or executed == None:
        # position closed, return amount
        return True, amount
    else:
        logging.error('problem with position checking %s %s', position, bar)
        return None, None

# orderDetails represents a ficitious order which:
#   fails to execute
#   opens and closes really fast (inside the next bar)
#   becomes a "position" representing shares held
# returns amount or None (error condition)
# need another value which is "continue"
# returns
#       True|False as to whether the trade executed
#       amount neg or pos (loss/gain) or None if unknown
def checkStopProfit(position, bar):
    amount = None
    executed = None
    # executed at stop price
    if position.stopOrder.auxPrice >= bar.low and position.profitOrder.lmtPrice > bar.high:
        amount = position.stopOrder.auxPrice - position.buyOrder.lmtPrice
        logging.info('closing position at a loss: {} {} {}'.format(amount, position, bar))
        executed = True
    # executed at profit price
    elif position.stopOrder.auxPrice < bar.low and position.profitOrder.lmtPrice <= bar.high:
        amount = position.profitOrder.lmtPrice - position.buyOrder.lmtPrice
        logging.info('closing position at a gain: {} {} {}'.format(amount, position, bar))
        executed = True
    # did not execute, no delta, stays as a position
    elif position.stopOrder.auxPrice < bar.low and position.profitOrder.lmtPrice > bar.high:
        logging.info('not closing a position {} {}'.format(position, bar))
        executed = False
        amount = None
    # unknown execution, assume loss
    elif position.stopOrder.auxPrice >= bar.low and position.profitOrder.lmtPrice <= bar.high:
        logging.info('wonky: closing position: {}'.format(position))
        executed = None
        amount = position.stopOrder.auxPrice - position.buyOrder.lmtPrice
    else:
        logging.fatal('unhandled {} {}'.format(position, bar))
    if amount is not None:
        amount = amount * position.buyOrder.totalQuantity
    return amount, executed
