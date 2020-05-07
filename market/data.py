import logging
import re

def histDataStreamError(reqId, errorCode, errorString, contract):
    re.compile('.*?API historical data query cancelled.*?')
    if errorCode != 162 and not re.match(errorString):
        logging.error('wrapper ERROR, Error {}, reqId {}: {}'.format(reqId, errorCode, errorString))

# defaults to getting auto-updated midpoint (bid/ask middle) outside regular trading hours for > 200 minutes with 1 min segments
# using utc timezones.  the final datapoint is the current minute, so len(histData)-2 is full last minute while -3 is prior window
# can feed to EMA and SMA to get the EMA on the fly
#
# duration (d) is specified in number of barSizes via lookupDuration
# FIXME: this kind of sucks
barSizeToDuration = {'1 min': {'unit': 'S', 'value': 60}}
def getHistData(wc, ibc, barSizeStr, longInterval, e='', d=None, t='MIDPOINT', r=False, f=2, k=True):
    duration = barSizeToDuration[barSizeStr]
    if not duration['unit'] or duration['unit'] != 'S' or not duration['value'] or not isinstance(duration['value'], int):
        raise RuntimeError('using seconds is supported')

    if d is not None: # we're doing a backtest, so add the long interval to build the SMA
        d = d *60*24 + longInterval
    else:
        d = longInterval * 2 + 5

    durationStr = ''
    if d > 1440: # d is in minutes because barSizeToDuration supports minutes atm
        d = int(d /60/24) if int(d /60/24) > 0 else 1
        durationStr = str(d) + ' D'
    else:
        durationStr = str(d *duration['value']) + ' ' + duration['unit']

    logging.info('getting historical data for c:{}/{}, e:{}, d:{}, b:{}, w:{}, u:{}, f:{}, k:{}'.format(wc.symbol, wc.localSymbol, e, durationStr, barSizeStr, t, r, f, k))
    histData = ibc.reqHistoricalData(contract=wc.contract, endDateTime=e, durationStr=durationStr, barSizeSetting=barSizeStr, whatToShow=t, useRTH=r, formatDate=f, keepUpToDate=k)
    return histData

def getMarketPrice(ticker):
    mp = ticker.marketPrice()
    if mp != mp:
        raise FloatingPointError('got floating point which is NaN')
    return mp

def getTick(wc, ibc):
    tick = ibc.reqMktData(contract=wc.contract, genericTickList='', snapshot=True, regulatorySnapshot=False)
    ibc.sleep(1)
    ibc.cancelMktData(contract=c)
    ibc.sleep(0)
    return tick

def getTicker(wc, ibc):
    ticker = ibc.reqMktData(contract=wc.contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
    ibc.sleep(0)
    return ticker

# histData is from getHistData
# so you can feed like 200 units of histData and get the 50 period sma by passing n = 50
# index is the index to start from (going backwards from the end of the [])
# this allows specifying tailOffset = 3 so EMA can be calculated using the most recent full datapoint
# eg the last bar is still filling, provided one is using keepUpToDate=True (vs False)
#
# to clarify further:
#
# histData[end] = currently filling bar (assuming k=True in call to getHistData, which is the default)
# histData[end-1] = latest data point
# histData[end-2] = previous full data point
# end = len(histData)-1
#
# so using SMA for the ``first'' EMA is now possible and calculating the EMA at any given time is ok
def calcSMA(n, histData, tailOffset=3):
    i = len(histData) - tailOffset
    j = n
    sma = 0
    while j > 0:
        sma += histData[i].close
        i -= 1
        j -= 1
    return sma / n

# exponential moving average (higher weighting recent data)
#
#   EMA = (v - prevEMA) * s + prevEMA
#
#       s = (2/ (n+1) ) [smoothing factor, weighting more toward recent prices)
#
#       v = current value
#
#       the first calculation is using the sma as the previous ema
#           since we have historical data, we can just calculate the sma on the fly and use i
def calcEMA(v, prevEMA, n):
    s = (2/ (n+1) )
    return (v - prevEMA) * s + prevEMA
