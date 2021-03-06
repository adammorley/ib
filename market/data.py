import logging
import re

from market import fatal

def dataStreamErrorHandler(reqId, errorCode, errorString, contract):
    rHdmsQueryCanceled = 162 # re.compile('.*?API historical data query cancelled.*?')
    rMdfOk = 2104 # re.compile('.*?Market data farm connection is OK.*?')
    # ok to ignore because no steady state connections
    rHdmsBroken = 2105 # re.compile('.*?HMDS data farm connection is broken.*?)
    rHdmsOk = 2106 # re.compile('.*?HMDS data farm connection is OK.*?')
    rHmdsDisconnectOk = 2107 # re.compile('.*?HMDS data farm connection is inactive but should be available upon demand.*?')
    rMdfDisconnectOk = 2108 # re.compile('.*?Market data farm connection is inactive but should be available upon demand.*?')
    rRthIgnored = 2109 # re.compile('.*?Attribute 'Outside Regular Trading Hours' is ignored based on the order type and destination.*?')
    rMdfC = 2119 # re.compile('.*?Market data farm is connecting.*?')
    errorCodes = [rHdmsQueryCanceled, rMdfOk, rHdmsBroken, rHdmsOk, rHmdsDisconnectOk, rMdfDisconnectOk, rRthIgnored, rMdfC]
    notFound = True
    for ec in errorCodes:
        if errorCode == ec:
            notFound = False
    if notFound:
        logging.error('wrapper, Error {}, reqId {}: {}'.format(errorCode, reqId, errorString))

# defaults to getting auto-updated midpoint (bid/ask middle) outside regular trading hours for > 200 minutes with 1 min segments
# using utc timezones.  the final datapoint is the current minute, so len(histData)-2 is full last minute while -3 is prior window
# can feed to EMA and SMA to get the EMA on the fly
#
# duration (d) is specified in number of barSizes via lookupDuration
# FIXME: this kind of sucks
barSizeToDuration = {'5 secs': {'unit': 'S', 'value': 5}, '1 min': {'unit': 'S', 'value': 60}}
def getHistData(wc, barSizeStr, longInterval, e='', d=None, t='MIDPOINT', r=False, f=2, k=False):
    duration = barSizeToDuration[barSizeStr]
    if not duration['unit'] or duration['unit'] != 'S' or not duration['value'] or not isinstance(duration['value'], int):
        fatal.errorAndExit('using seconds is supported')

    durationStr = ''
    if d is not None: # doing a backtest, so add the long interval to build the SMA
        d = d *60*60 + longInterval*duration['value'] # force to seconds, then back up to bar size
        if d > 86400: # d is in minutes because barSizeToDuration supports minutes atm
            d = int(d /60/60) if int(d /60/60) > 0 else 1
            durationStr = str(d) + ' D'
        else:
            durationStr = str(d) + ' S'
    else: # not doing a backtest
        # add one because when market closed, latest bar is not yet ready (crazy but true)
        # happens especially when there are two closes (like with the futures maintenace
        # window)
        d = 2 * longInterval +1
        durationStr = str(d *duration['value']) + ' ' + duration['unit']

    logging.info('getting historical data for c:{}/{}, e:{}, d:{}, b:{}, w:{}, u:{}, f:{}, k:{}'.format(wc.symbol, wc.localSymbol, e, durationStr, barSizeStr, t, r, f, k))
    histData = wc.ibClient.reqHistoricalData(contract=wc.contract, endDateTime=e, durationStr=durationStr, barSizeSetting=barSizeStr, whatToShow=t, useRTH=r, formatDate=f, keepUpToDate=k)
    return histData

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
def calcSMA(interval, data, startIndex):
    sma = 0
    for i in range(startIndex, startIndex+interval):
        try:
            sma += data[i].close
        except (AttributeError, KeyError):
            sma += histData[i]
    return sma/interval

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
