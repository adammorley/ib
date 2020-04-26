import logging

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
