import logging

# defaults to getting auto-updated midpoint (bid/ask middle) outside regular trading hours for > 200 minutes with 1 min segments
# using utc timezones.  the final datapoint is the current minute, so len(histData)-2 is full last minute while -3 is prior window
# can feed to EMA and SMA to get the EMA on the fly
#
# duration (d) is specified in number of barSizes via lookupDuration
barSizeToDuration = {'1 min': {'unit': 'S', 'value': 60}}
def getHistData(c, ibc, barSizeStr, longInterval, e='', t='MIDPOINT', r=False, f=2, k=True):
    duration = barSizeToDuration[barSizeStr]
    if not duration['unit'] or duration['unit'] != 'S' or not duration['value'] or type(duration['value']) != int:
        raise RuntimeError('using seconds is supported')
    durationStr = str(duration['value'] * longInterval * 2 + 5 * duration['value']) + ' ' + duration['unit']
    logging.info('getting historical data for c:{}/{}, e:{}, d:{}, b:{}, w:{}, u:{}, f:{}, k:{}'.format(c.symbol, c.localSymbol, e, durationStr, barSizeStr, t, r, f, k))
    histData = ibc.reqHistoricalData(contract=c, endDateTime=e, durationStr=durationStr, barSizeSetting=barSizeStr, whatToShow=t, useRTH=r, formatDate=f, keepUpToDate=k)
    return histData

def getMarketPrice(ticker):
    mp = ticker.marketPrice()
    if mp != mp:
        raise FloatingPointError('got floating point which is NaN')
    return mp

def getTick(c, ibc):
    tick = ibc.reqMktData(contract=c, genericTickList='', snapshot=True, regulatorySnapshot=False)
    ibc.sleep(1)
    ibc.cancelMktData(contract=c)
    ibc.sleep(0)
    return tick

def getTicker(c, ibc):
    ticker = ibc.reqMktData(contract=c, genericTickList='', snapshot=False, regulatorySnapshot=False)
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
#   EMA = (v - sma) * s + sma
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
