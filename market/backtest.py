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

def backtest(wc, dataStream, dataStore, conf):
    totals = {'gl': 0, 'tf': 0, 'mf': 0}
    positions = []
    startIndex = None
    # which data point in the dataStream/bar set to evaluate on this round about buy or not
    if conf.detector == 'threeBarPattern':
        startIndex = 2
    elif conf.detector == 'emaCrossover':
        # we just stored (at init) the last EMA calculated, eg we are examining curClosePriceIndex
        startIndex = dataStore.curEmaIndex + 1

    for i in range(startIndex, len(dataStream)-1):
        if conf.detector == 'threeBarPattern':
            dataStore = updateBarSet(dataStream, i, dataStore)
    
        # first, see if any positions changed
        logging.info('number of positions open: {}'.format(len(positions)))
        positions, totals = checkPositions(wc, positions, conf, dataStore, dataStream, i, totals)
    
        # see if we calculated a buyPrice
        buyPrice = None
        if conf.detector == 'threeBarPattern':
            buyPrice = dataStore.analyze()
        elif conf.detector == 'emaCrossover':
            buyPrice = dataStore.checkForBuy(dataStream)
    
        if buyPrice is not None:
            od = order.OrderDetails(buyPrice, conf, wc)
            od.config.qty = order.calculateQty(od)
            logging.warn('found an order: %s %s', od, dataStore)
            if len(positions) < od.config.openPositions:
                # checking whether the position opened and closed in the same bar
                amount = None
                orders = order.CreateBracketOrder(od)
                # need to use real values (not offsets) for position checker
                if orders.stopOrder.orderType == 'TRAIL': # have to store for position tracking
                    if orderDetails.config.stopPercent:
                        orders.stopOrder.auxPrice = order.Round( orders.buyOrder.lmtPrice *(100.0 - orders.stopOrder.trailingPercent)/100.0, od.wContract.priceIncrement)
                    elif orderDetails.config.stopTarget:
                        orders.stopOrder.auxPrice = orders.buyOrder.lmtPrice - orderDetails.config.stopTarget
                if conf.detector == 'threeBarPattern':
                    orders, amount = checkTradeExecution(dataStore.third, orders)
                elif conf.detector == 'emaCrossover':
                    orders, amount = checkTradeExecution(dataStream[dataStore.curIndex], orders)
                logging.warn('position config %s', od.config)
                # check if the trade executed
                if orders is not None:
                    logging.warn('opened a position: %s', orders)
                    positions.append(orders)
                    totals['tf'] += orders.buyOrder.lmtPrice * orders.buyOrder.totalQuantity
                elif orders is None and amount is not None:
                    logging.warn('opened and closed a position in third bar')
                    totals['gl'] += amount
                logging.debug('totalFundsInPlay: %.2f', totals['tf'])
    return totals

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
