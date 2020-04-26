import logging

from market import bars

def anotateBars(histBars):
    newBars = []
    for i in range(0, len(histBars)):
        newBars.append(makeBar(histBars[i]))
        newBars[i].anotate()
    return newBars

def makeBar(histBar):
    bar = bars.Bar()
    bar.open = histBar.open
    bar.close = histBar.close
    bar.high = histBar.high
    bar.low = histBar.low
    return bar

def getNextBar(newBars, index):
    return newBars[index]

# only used to check the third bar for if the order bought/sold in the third bar during "blur"
def checkTradeExecution(bar, trade):
    if trade.buyPrice <= bar.high and trade.buyPrice - trade.config.stopTarget >= bar.low:
        return None, (-1 * trade.config.stopTarget)
    else:
        return trade, None

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
    if position.buyPrice - position.config.stopTarget >= bar.low and position.buyPrice + position.config.profitTarget > bar.high:
        amount = (-1 * position.config.stopTarget) * position.config.qty
        logging.debug('closing position at a loss: %.2f %s %s', amount, position, bar)
        executed = True
    # executed at profit price
    elif position.buyPrice - position.config.stopTarget < bar.low and position.buyPrice + position.config.profitTarget <= bar.high:
        amount = position.config.profitTarget * position.config.qty
        logging.debug('closing position at a gain: %.2f %s %s', amount, position, bar)
        executed = True
    # did not execute, no delta, stays as a position
    elif position.buyPrice - position.config.stopTarget < bar.low and position.buyPrice + position.config.profitTarget > bar.high:
        logging.debug('not closing a position: %s, %s', position, bar)
        executed = False
        amount = None
    # unknown execution, assume loss
    elif position.buyPrice - position.config.stopTarget >= bar.low and position.buyPrice + position.config.profitTarget <= bar.high:
        logging.debug('wonky: closing position: %s', position)
        executed = None
        amount = (-1 * position.config.stopTarget) * position.config.qty
    else:
        logging.fatal('unhandled %s %s', position, bar)
    return amount, executed

