import logging
import re

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

def getNextBar(dataStream, index):
    return dataStream[index]

def setupThreeBar(dataStream, period):
    index = len(dataStream)-1 - period *24*60
    dataStore = bars.BarSet()
    dataStore.first = getNextBar(dataStream, index)
    dataStore.second = getNextBar(dataStream, index+1)
    dataStore.third = getNextBar(dataStream, index+2)
    return index+3, dataStore

def backtest(wc, dataStream, dataStore, conf, period):
    totals = {'gl': 0, 'tf': 0, 'mf': 0, 'op': 0}
    positions = []
    startIndex = None
    # which data point in the dataStream/bar set to evaluate on this round about enter or not
    if conf.detector == 'threeBarPattern':
        startIndex, dataStore = setupThreeBar(dataStream, period)
    elif conf.detector == 'emaCrossover':
        # FIXME: might be a bug here
        # we just stored (at init) the last EMA calculated, eg we are examining curClosePriceIndex
        startIndex = dataStore.curEmaIndex + 1

    for i in range(startIndex, len(dataStream)-1):
        # first, see if any positions changed
        logging.info('number of positions open: {}'.format(len(positions)))
        positions, totals = checkPositions(wc, positions, conf, dataStore, dataStream, i, totals)
    
        # see if we calculated an entryPrice
        entryPrice = None
        if conf.detector == 'threeBarPattern':
            entryPrice = dataStore.analyze()
        elif conf.detector == 'emaCrossover':
            entryPrice = dataStore.checkForBuy(dataStream)
    
        if entryPrice is not None:
            od = order.OrderDetails(entryPrice, conf, wc)
            od.config.qty = order.calculateQty(od)
            logging.warn('found an order: %s %s', od, dataStore)
            if len(positions) < od.config.openPositions:
                # checking whether the position opened and closed in the same bar
                amount = None
                orders = order.CreateBracketOrder(od)
                # need to use real values (not offsets) for position checker
                if orders.stopOrder.orderType == 'TRAIL': # have to store for position tracking
                    if od.config.stopPercent:
                        orders.stopOrder.auxPrice = order.Round( orders.entryOrder.lmtPrice *(100.0 - orders.stopOrder.trailingPercent)/100.0, od.wContract.priceIncrement)
                    elif od.config.stopTarget:
                        orders.stopOrder.auxPrice = orders.entryOrder.lmtPrice - orderDetails.config.stopTarget
                if conf.detector == 'threeBarPattern':
                    orders, amount = checkTradeExecution(dataStore.third, orders)
                elif conf.detector == 'emaCrossover':
                    orders, amount = checkTradeExecution(dataStream[dataStore.curEmaIndex+1], orders)
                logging.warn('position config %s', od.config)
                # check if the trade executed
                if orders is not None:
                    logging.warn('opened a position: %s', orders)
                    positions.append(orders)
                    totals['tf'] += orders.entryOrder.lmtPrice * orders.entryOrder.totalQuantity
                    totals['op'] += orders.entryOrder.totalQuantity
                elif orders is None and amount is not None:
                    logging.warn('opened and closed a position in third bar')
                    totals['gl'] += amount
                logging.debug('totalFundsInPlay: %.2f', totals['tf'])
        if conf.detector == 'threeBarPattern':
            dataStore.first = dataStore.second
            dataStore.second = dataStore.third
            dataStore.third = getNextBar(dataStream, i)
    if len(positions) != 0:
        positions, totals = checkPositions(wc, positions, conf, dataStore, dataStream, i, totals)
        for p in positions:
            totals['lo'] = (dataStream[len(dataStream)-1].close - p.entryOrder.lmtPrice) *p.entryOrder.totalQuantity
    return totals

# only used to check the third bar for if the order bought/sold in the third bar during "blur"
# eg this is an unknown because we aren't analyzing by-second data
def checkTradeExecution(bar, orders):
    if orders.entryOrder.lmtPrice <= bar.high and orders.stopOrder.auxPrice >= bar.low:
        return None, (orders.stopOrder.auxPrice - orders.entryOrder.lmtPrice)
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
            totals['tf'] -= position.entryOrder.lmtPrice * position.entryOrder.totalQuantity
            positions.remove(position)
        elif not closed and position.stopOrder.orderType == 'TRAIL':
            closePrice = dataStream[index].close
            if closePrice > position.entryOrder.lmtPrice:
                if position.stopOrder.trailingPercent:
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
    if position.stopOrder.auxPrice >= bar.low and position.exitOrder.lmtPrice > bar.high:
        amount = position.stopOrder.auxPrice - position.entryOrder.lmtPrice
        logging.info('closing position at a loss: {} {} {}'.format(amount, position, bar))
        executed = True
    # executed at profit price
    elif position.stopOrder.auxPrice < bar.low and position.exitOrder.lmtPrice <= bar.high:
        amount = position.exitOrder.lmtPrice - position.entryOrder.lmtPrice
        logging.info('closing position at a gain: {} {} {}'.format(amount, position, bar))
        executed = True
    # did not execute, no delta, stays as a position
    elif position.stopOrder.auxPrice < bar.low and position.exitOrder.lmtPrice > bar.high:
        logging.info('not closing a position {} {}'.format(position, bar))
        executed = False
        amount = None
    # unknown execution, assume loss
    elif position.stopOrder.auxPrice >= bar.low and position.exitOrder.lmtPrice <= bar.high:
        logging.info('wonky: closing position: {}'.format(position))
        executed = None
        amount = position.stopOrder.auxPrice - position.entryOrder.lmtPrice
    else:
        logging.fatal('unhandled {} {}'.format(position, bar))
    if amount is not None:
        amount = amount * position.entryOrder.totalQuantity
    return amount, executed







########################DRAGONS!
def processScriptOutput():
    ds = {}
    with open('../esData', 'r') as f:
        while True:
            s = f.readline()
            if not s:
                break
            kv = s.split()
            vh = kv[1].split(':')
            try:
                ds[kv[0]][vh[0]] = vh[1]
            except KeyError:
                ds[kv[0]] = {}
                ds[kv[0]][vh[0]] = vh[1]
    one={}
    five={}
    ten={}
    fourteen={}
    thirty={}
    sixty={}
    total = {}
    for k, v in ds.items():
        for d, gl in v.items():
            d = int(d)
            gl = float(gl)
            if d == 1:
                one[k] = gl
            elif d == 5:
                five[k] = gl
            elif d == 10:
                ten[k] = gl
            elif d == 14:
                fourteen[k] = gl
            elif d == 30:
                thirty[k] = gl
            elif d == 60:
                sixty[k] = gl
    return one, five, ten, fourteen, thirty, sixty

# send output of processscriptoutput
# inFromOut is output of script outputthing above
def findUnion(inFromOut):
    best = set()
    for arr in inFromOut:
        i = 0
        for k in sorted(arr, key=arr.get, reverse=True):
            i += 1
            if i > 30:
                break
            best.add(k)
    return best

# regex is like 'lI:40,sI:15,w:15,sT:5,pT:7'
def filterBest(regex, inFromOut):
    #r = re.compile('lI:40,sI:15,w:(5|15),sT.*')
    r = re.compile(regex)
    for arr in inFromOut:
        print('mark')
        for k in sorted(arr, key=arr.get, reverse=True):
            m = r.match(k)
            if m:
                print(k, arr[k])

def feedFromUnionToPositiveKeyFinder(best, mult, inFromOut):
    d = {}
    for k in best:
        r = getFromIn(k, mult, inFromOut)
        if r:
            # FIXME: make -1
            for i in range(len(inFromOut)-1, 0, -1):
                try:
                    t = None
                    t = inFromOut[i][k]
                    if t is not None:
                        d[k] = t
                        break
                except KeyError:
                    zz =5
    return d

def getBestValue(inFromOut):
    best = findUnion(inFromOut)
    ds = []
    for i in [1.5, 2, 2.5, 3]:
        print('at multiplier ', i)
        d = feedFromUnionToPositiveKeyFinder(best, i, inFromOut)
        for k, v in d.items():
            if v > 20000:
                print(k, v)
        print('')

def getFromIn(key, mult, inFromOut):
    v = []
    for i in inFromOut:
        try:
            v.append(i[key])
        except KeyError:
            zzz = 5
    p = v[0]
    f = False
    for j in v:
        if j < 1:
            f = False
            break
        elif j > mult * p:
            f = True
        else:
            f = False
        p = j
    if f:
        return key
    return None


