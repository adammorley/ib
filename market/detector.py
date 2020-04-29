# functions to detect changes which indicate a buy point for various securities
import logging

from market import bars
from market import data

# get the next minute's bar
def GetNextBar(ticker, sleepFunc):
    numberOfTicksInBar = 240
    sleepSecs = 0.250
    logging.debug('getting points every 250ms')

    bar = bars.Bar(ticker.marketPrice())
    for i in range(0, numberOfTicksInBar):
        sleepFunc(sleepSecs)
        m = ticker.marketPrice()
        if m > bar.high:
            bar.high = m
        elif m < bar.low:
            bar.low = m
    bar.close = ticker.marketPrice()
    bar.cleanUp()
    bar.anotate()
    return bar

# a three bar pattern is a set of three bars where it's g/r/g or r/g/r
# indicating a momentum change
def threeBarPattern(barSet, ticker, sleepFunc):
    if barSet.first is None and barSet.second is None:
        barSet.first = GetNextBar(ticker, sleepFunc)
        barSet.second = GetNextBar(ticker, sleepFunc)
    else:
        barSet.first = barSet.second
        barSet.second = barSet.third
    barSet.third = GetNextBar(ticker, sleepFunc)
    return barSet.analyze()

# EMA tracks two expoential moving averages
# a long and a short
class EMA:
    short: float
    long_: float
    isCrossed: bool = None
    previousState: bool = None
    stateChanged: bool = None
    areWatching: bool = None
    countOfCrossedIntervals: int = 0
    shortInterval: int = 50
    longInterval: int = 200

    def __init__(self, short, long_, shortInterval, longInterval):
        if shortInterval is not None:
            self.shortInterval = shortInterval
        if longInterval is not None:
            self.longInterval = longInterval
        self.update(short, long_)

    def update(self, short, long_):
        if isCrossed is not None:
            self.previousState = self.isCrossed
        self.short = short
        self.logn = long_
        self.isCrossed = True if self.short > self.long else False
        if isCrossed is not None and previousState is not None:
            if self.isCrossed != self.previousState:
                self.stateChanged = True
            else:
                self.stateChanged = False

    def checkForBuy(self, dataStream, sleepFunc):
        sleepFunc(60) # if you change this, be sure to understand the call to data.getHistData and the p argument
        emaShort, emaLong = data.getEMA(dataStream, self.shortInterval, self.longInterval)
        self.update(emaShort, emaLong)
        if not self.areWatching and self.stateChanged and self.isCrossed: # short crossed long, might be a buy, flag for re-inspection
            self.areWatching = True
            self.countOfCrossedIntervals = 0
        elif self.areWatching and self.stateChanged and not self.isCrossed: # watching for consistent crossover, didn't get it
            self.areWatching = False
            self.countOfCrossedIntervals = 0
        elif self.areWatching and not self.stateChanged and ema.isCrossed: # watching, and it's staying set
            self.countOfCrossedIntervals += 1
    
        if self.areWatching and self.countOfCrossedIntervals > 5: # FIXME: what happens if 60 seconds above and 1 min default in data.getHistData change?
            self.areWatching = False
            self.countOfCrossedIntervals = 0
            marketPriceIndex = len(dataStream) - 1 # See note in data module for SMA
            return dataStream[marketPriceIndex].marketPrice() # buyPrice
