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
    short: float = 0
    long_: float = 0
    isCrossed: bool = None
    previousState: bool = None
    stateChanged: bool = None
    areWatching: bool = None
    countOfCrossedIntervals: int = 0
    shortInterval: int = 50
    longInterval: int = 200
    barSizeStr: str = None
    sleepTime: int = None


    def __init__(self, barSizeStr, shortInterval=None, longInterval=None):
        if shortInterval is not None:
            self.shortInterval = shortInterval
        if longInterval is not None:
            self.longInterval = longInterval
        dur = data.barSizeToDuration[barSizeStr]
        if dur['unit'] != 'S' or not dur['value'] or not isinstance(dur['value'], int):
            raise RuntimeError('re-factor')
        self.sleepTime = dur['value']

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def update(self, short, long_):
        if self.isCrossed is not None:
            self.previousState = self.isCrossed
        self.short = short
        self.long = long_
        self.isCrossed = True if self.short > self.long else False
        if self.isCrossed is not None and self.previousState is not None:
            if self.isCrossed != self.previousState:
                self.stateChanged = True
            else:
                self.stateChanged = False
        logging.info('updated ema: %s', self)

    def calcInitEMAs(self, dataStream):
        short = 0
        long_ = 0
        logging.info('datastream is {}'.format(len(dataStream)))
        for interval in [self.shortInterval, self.longInterval]:
            # first we calculate the SMA over the interval (going backwards) one interval back in the dataStream
            tailOffset = len(dataStream) - 1 - interval - 2 # See note in data.SMA
            sma = data.calcSMA(interval, dataStream, tailOffset)
            logging.info('calculated sma of {} for {} at {}'.format(sma, interval, tailOffset))

            prevEMA = sma
            ema = 0
            index = len(dataStream) - 1 - interval - 1 # See note in data.SMA
            for point in range(0, interval):
                curPrice = dataStream[index].close
                ema = data.calcEMA(curPrice, prevEMA, interval)
                prevEMA = ema
                index += 1
            logging.info('calculated ema for {} as {}'.format(interval, ema))
            if interval == self.shortInterval:
                short = ema
            elif interval == self.longInterval:
                long_ = ema
        self.update(short, long_)

    def recalcEMAs(self, dataStream):
        curPriceIndex = len(dataStream) - 2 # See note in data.SMA
        curPrice = dataStream[curPriceIndex].close
        logging.info('recalculating emas at index {} using last minutes price of {}'.format(curPriceIndex, curPrice))
        short = data.calcEMA(curPrice, self.short, self.shortInterval)
        long_ = data.calcEMA(curPrice, self.long, self.longInterval)
        self.update(short, long_)

    def checkForBuy(self, dataStream, sleepFunc):
        logging.info('waiting for data to check for buy...')
        sleepFunc(self.sleepTime) # if you change this, be sure to understand the call to data.getHistData and the p argument
        self.recalcEMAs(dataStream)
        logging.info('before checks: %s', self)
        if not self.areWatching and self.stateChanged and self.isCrossed: # short crossed long, might be a buy, flag for re-inspection
            self.areWatching = True
            self.countOfCrossedIntervals = 0
        elif self.areWatching and self.stateChanged and not self.isCrossed: # watching for consistent crossover, didn't get it
            self.areWatching = False
            self.countOfCrossedIntervals = 0
        elif self.areWatching and not self.stateChanged and self.isCrossed: # watching, and it's staying set
            self.countOfCrossedIntervals += 1
        logging.info('after checks: %s', self)
        if not self.areWatching and self.isCrossed: # FIXME: hack
            self.areWatching=True
            self.countOfCrossedIntervals=1
            logging.fatal('HACK: forcing buy')
    
        if self.areWatching and self.countOfCrossedIntervals > 5:
            self.areWatching = False
            self.countOfCrossedIntervals = 0
            closePriceIndex = len(dataStream) - 1 # See note in data module for SMA
            closePrice = dataStream[closePriceIndex].close
            logging.info('returning a buy at index {} of {} for {}'.format(closePriceIndex, closePrice, self))
            return closePrice # buyPrice
