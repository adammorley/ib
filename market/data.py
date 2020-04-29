import logging

# defaults to getting auto-updated midpoint (bid/ask middle) outside regular trading hours for > 200 minutes with 1 min segments
# using utc timezones.  the final datapoint is the current minute, so len(histData)-2 is full last minute while -3 is prior window
# can feed to EMA and SMA to get the EMA on the fly
def getHistData(c, ibc, e='', d=12300, p='1 min', t='MIDPOINT', r=False, f=2, k=True):
    histData = ibc.reqHistoricalData(contract=c, endDate=e, durationStr=str(d)+' S', barSizeSetting=p, whatToShow=t, useRTH=r, formatDate=f, keepUpToDate=k)
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
# index is the index to start from (going backwards)
# this allows specifying index = 3 so EMA can be calculated using the most recent full datapoint
# eg the last bar is still filling, provided one is using keepUpToDate=True (vs False)
#
# so:
# h = data.getHistData(...)
# v = len(EMA) - 2
# ema50 = data.EMA(h[v], data.SMA(h, 3, 50), 50)
# ema200 = data.EMA(h[v], data.SMA(h, 3, 200), 200)
# if ema50 > ema200:
#   crossover = True
# ibc.sleep(60)
def calcSMA(n, histData, nindex=3):
    i = len(histData) - nindex
    j = n
    sma = 0
    while n > 0:
        sma += histData[i].close
        i -= 1
        j -= 1
    return sma / n

# exponential moving average (higher weighting recent data
#
#   EMA = (v - sma) * s + sma
#
#       s = (2/ (n+1) ) [smoothing factor, weighting more toward recent prices)
#
#       v = current value
#
#       the first calculation is using the sma as the previous ema
#           since we have historical data, we can just calculate the sma on the fly and use i
def calcEMA(v, sma, n):
    s = (2/ (n+1) )
    return (v - sma) * s + sma

def getEMA(histData, shortInterval, longInterval):
    curPriceIndex = len(histData) - 2 # See note in data module for SMA
    emaShort = calcEMA(histData[curPriceIndex], calcSMA(shortInterval, histData), shortInterval)
    emaLong = calcEMA(histData[curPriceIndex], calcSMA(longInterval, histData), longInterval)
    return emaShort, emaLong
