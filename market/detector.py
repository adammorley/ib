# functions to detect changes which indicate an entry point for various securities
import datetime
import logging
import math
import sys
import time

from market import bars
from market import data
from market import date
from market import fatal

# https://github.com/adammorley/ib/issues/7
def connectivityError(reqId, errorCode, errorString, contract):
    rConnectivityLost = 1100 # re.compile('.*?Connectivity between IB and Trader Workstation has been lost.*?')
    rConnectivityRestoredDataLost = 1101 # re.compile('.*?Connectivity between IB and TWS has been restored- data lost.*?')
    rMdfDisconnect = 2103 # re.compile('.*?Market data farm connection is inactive but should be available upon demand.*?')
    rCompetingSessions = 10197 # re.compile('.*?No market data during competing live session.*?')
    errorCodes = [rConnectivityLost, rConnectivityRestoredDataLost, rMdfDisconnect, rCompetingSessions]
    for ec in errorCodes:
        if errorCode == ec:
            logging.error('received an error which requires restart, pausing briefly before restart: {} {}'.format(errorCode, errorString))
            time.sleep(30)
            sys.exit(0)

    rConnectivityRestoredNoDataLoss = 1102 # re.compile('.*?Connectivity between IB and Trader Workstation has been restored - data maintained.*?')
    infoCodes = [rConnectivityRestoredNoDataLoss]
    for ic in infoCodes:
        if errorCode == ic:
            logging.warn('received an info: {} {}'.format(errorCode, errorString))

# max loss is actually qty * open positions * stop size * tick value + maxloss, eg this is a trigger, not a protection
# FIXME: add dynamic handling on open orders (eg closing positions) and more betterer
#        because at the moment, taking a dep on order execution system
# https://interactivebrokers.com/php/whiteLabel/TWS_Reference_Information/pnl_.htm
def lossTooHigh(wc, conf):
    wc.updatePnl(conf.account)
    if math.isnan(wc.pnl.realizedPnL):
        return False # returns NaN when zero, different from .portfolio()
    elif wc.pnl.realizedPnL < 0 and abs(wc.pnl.realizedPnL) > conf.maxLoss:
        return True
    return False

def setupData(wc, conf, backtestArgs=None):
    dataStore = None
    dataStream = None
    if conf.detector == 'threeBarPattern':
        dataStore = barSet = bars.BarSet()
    if backtestArgs is not None:
        logging.fatal('WARNING: DOING A BACKTEST, NOT USING LIVE DATA')
        if conf.detector == 'Crossover':
            dataStore = Crossover(conf.barSizeStr, wc, backtestArgs['shortInterval'], backtestArgs['longInterval'], backtestArgs['watchCount'])
            dataStore.backTest = True
            dataStream = data.getHistData(wc, barSizeStr=conf.barSizeStr, longInterval=dataStore.longInterval, e=backtestArgs['e'], d=backtestArgs['d'], t=backtestArgs['t'], r=backtestArgs['r'], f=backtestArgs['f'], k=backtestArgs['k'])
            dataStore.initIndicators(dataStream)
        else:
            dataStream = data.getHistData(wc, barSizeStr=conf.barSizeStr, longInterval=backtestArgs['longInterval'], e=backtestArgs['e'], d=backtestArgs['d'], t=backtestArgs['t'], r=backtestArgs['r'], f=backtestArgs['f'], k=backtestArgs['k'])
    elif conf.detector == 'threeBarPattern':
        dataStream = wc.getTicker()
    elif conf.detector == 'Crossover':
        dataStore = Crossover(conf.barSizeStr, wc, conf.shortEMA, conf.longEMA, conf.watchCount)

        # disable wrapper logging to hide the API error for canceling the data every hour
        logging.getLogger('ib_insync.wrapper').setLevel(logging.CRITICAL)
        logging.warn('ignoring hdms broken errors')
        wc.ibClient.errorEvent += data.dataStreamErrorHandler

        logging.warn('installing auto restart handler.')
        wc.ibClient.errorEvent += connectivityError

        useRth = False if conf.enterOutsideRth else True
        histData = data.getHistData(wc, barSizeStr=conf.barSizeStr, longInterval=dataStore.longInterval, r=useRth)
        if len(histData) < dataStore.longInterval *2:
            fatal.fatal(conf, 'did not get back the right amount of data from historical data call, perhaps broken?')
        dataStore.initIndicators(histData)
        wc.realtimeBars()
    else:
        fatal.errorAndExit('do not know what to do!')
    return dataStore, dataStream

# get the next minute's bar
def GetNextBar(ticker, sleepFunc):
    numberOfTicksInBar = 60
    sleepSecs = 1
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

from market.contract import wContract
# EMA tracks two expoential moving averages
# a long and a short
class Crossover:
    wContract: wContract
    short: float = 0
    long_: float = 0
    macd: float = 0
    macdSignal: float = None
    macdSignalValues: list
    macdSize: int = 9 # default to nine period macd signal
    shortEMAoverLongEMA: bool = None
    previousState: bool = None
    stateChanged: bool = None
    count: int = 0
    entryAction: str = None
    prevMidpoint: float = None
    watchCount: int = 5 # barSizeSetting intervals
    watchMidpoint: int # midpoint at start of watch
    shortInterval: int = 5
    longInterval: int = 20
    barSizeStr: str = None
    barSize: int = None # seconds
    backTest: bool = None
    curEmaIndex: int = None
    byPeriod: int = None # number of days of bars to examine during iterative backtest

    def __init__(self, barSizeStr, wContract, shortInterval=None, longInterval=None, watchCount=None):
        if shortInterval is not None:
            self.shortInterval = shortInterval
        if longInterval is not None:
            self.longInterval = longInterval
        if watchCount is not None:
            self.watchCount = watchCount
        dur = data.barSizeToDuration[barSizeStr]
        self.wContract = wContract
        if dur['unit'] != 'S' or not dur['value'] or not isinstance(dur['value'], int):
            fatal.errorAndExit('re-factor')
        self.barSize = dur['value']

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def updateIndicators(self, short, long_):
        if self.shortEMAoverLongEMA is not None:
            self.previousState = self.shortEMAoverLongEMA
        self.short = short
        self.long = long_
        self.macd = short - long_
        self.updateMacdSignalValues()
        self.updateMacdSignal()
        self.shortEMAoverLongEMA = True if self.short > self.long else False
        if self.shortEMAoverLongEMA is not None and self.previousState is not None:
            if self.shortEMAoverLongEMA != self.previousState:
                self.stateChanged = True
            else:
                self.stateChanged = False
        logging.info('updated ema: %s', self)
    def updateMacdSignalValues(self):
        if self.macdSignal is None:
            try:
                self.macdSignalValues.append(self.macd)
            except AttributeError:
                self.macdSignalValues = []
                self.macdSignalValues.append(self.macd)
    # this is safe because historical data is used (of longInterval size) to track
    # the initialization values.  if longInterval < 2*macdSize, might be off for
    # the first few data points
    def updateMacdSignal(self):
        if self.macdSignal is None and len(self.macdSignalValues) == self.macdSize:
            self.macdSignal = data.calcSMA(self.macdSize, self.macdSignalValues, 0)
        elif self.macdSignal is not None:
            self.macdSignal = data.calcEMA(self.macd, self.macdSignal, self.macdSize)

    def initIndicators(self, dataStream):
        short = 0
        long_ = 0
        logging.info('datastream is {}'.format(len(dataStream)))
        for interval in [self.shortInterval, self.longInterval]:
            if self.backTest: # in backtest, we can just start from 0 instead of later
                sma = 0
                startIndex = 0
                if self.byPeriod:
                    startIndex = len(dataStream)-1 - int(self.byPeriod *60*60 /self.barSize)
                    logging.info('doing by period, using index/period(hours): {}/{}'.format(startIndex, self.byPeriod))
                sma = data.calcSMA(interval, dataStream, startIndex)
                # FIXME: might be a bug here, because interval calculations
                ema = data.calcEMA(dataStream[startIndex+interval].close, sma, interval)
                self.curEmaIndex = startIndex+interval
            else:
                # first we calculate the SMA over the interval (going backwards) one interval back in the dataStream
                smaStartIndex = len(dataStream)-1 - interval*2
                if interval == self.longInterval and smaStartIndex < 0:
                    fatal.errorAndExit('wrong interval calc: {} {} {}'.format(smaStartIndex, len(dataStream), interval))
                sma = data.calcSMA(interval, dataStream, smaStartIndex)
                logging.info('calculated sma of {} for {} starting at {}'.format(sma, interval, smaStartIndex))
    
                prevEMA = sma
                ema = 0
                index = len(dataStream)-1 - interval
                for point in range(index, len(dataStream)):
                    midpoint = dataStream[index].close
                    ema = data.calcEMA(midpoint, prevEMA, interval)
                    prevEMA = ema
                    index += 1
            logging.info('calculated ema for {} as {}'.format(interval, ema))
            if interval == self.shortInterval:
                short = ema
            elif interval == self.longInterval:
                long_ = ema
        self.updateIndicators(short, long_)
    def recalcIndicators(self, dataStream):
        midpoint = None
        if self.backTest:
            self.curEmaIndex = self.curEmaIndex + 1
            midpoint = dataStream[self.curEmaIndex].close
            logging.info('recalculating indicators at index {} using price of {}'.format(self.curEmaIndex, midpoint))
        else:
            midpoint = self.wContract.realtimeMidpoint()
            logging.info('recalculating indicators using market midpoint of {}'.format(midpoint))

        if math.isnan(midpoint):
            fatal.fatal('getting an NaN from midpoint call during open market conditions, do not know how to handle missing bid/ask during open hours {} {}'.format(midpoint, self.wContract.contract))

        short = data.calcEMA(midpoint, self.short, self.shortInterval)
        long_ = data.calcEMA(midpoint, self.long, self.longInterval)
        self.updateIndicators(short, long_)
        return midpoint

    # the rules for entry:
    #
    #   if the short-term ema crossed and is above the long-term ema for n (watchCount) intervals
    #       can enter buy side
    #       reverse is sell side
    def checkForEntry(self, dataStream, sleepFunc=None):
        if not self.backTest:
            sleepFunc(self.barSize) # if you change this, be sure to understand the call to data.getHistData and the p argument

        midpoint = self.recalcIndicators(dataStream)
        lowMidpoint, highMidpoint = self.wContract.realtimeLowMidpoint(), self.wContract.realtimeHighMidpoint()
        lowBid = self.wContract.realtimeLowBid()
        logging.info('before checks: %s', self)
        if self.count > 0 and self.entryAction == 'BUY' and midpoint < self.long:
            logging.warn('midpoint fell below long ema during buy watch, stopping watch')
            self.count = 0
        elif self.count > 0 and self.entryAction == 'SELL' and midpoint > self.long:
            logging.warn('midpoint went above long ema during sell watch, stopping watch')
            self.count = 0
        elif self.count > 0 and self.entryAction == 'BUY' and self.prevMidpoint is not None and midpoint <= self.prevMidpoint:
            logging.warn('weak momentum signal, midpoints crossing')
            self.count = 0
        elif self.count > 0 and self.entryAction == 'SELL' and self.prevMidpoint is not None and midpoint >= self.prevMidpoint:
            logging.warn('weak momentum signal, midpoints crossing')
            self.count = 0
        # FIXME: the below is really more of a "is the first order derivative for short higher than long?"
        elif self.count > 0 and self.entryAction == 'BUY' and self.long + 0.125 > self.short:
            logging.warn('not enough momentum, short and long too close.')
            self.count = 0
        elif self.stateChanged:
            self.count = 1
            self.watchMidpoint = midpoint
            if self.shortEMAoverLongEMA:
                self.entryAction = 'BUY'
            else:
                self.entryAction = 'SELL'
        elif self.count and not self.stateChanged:
            self.count += 1
        else:
            self.count = 0
        logging.info('after checks: %s', self)
        logging.warn('entryCalcs: shortEMA: {:.3f}/longEMA: {:.3f} using midpoint: {}, prevMidpoint: {}, lowBid: {}; states: count: {}, entryAction: {}, shortEMAoverLongEMA: {}, stateChanged: {}'.format(self.short, self.long, midpoint, self.prevMidpoint, lowBid, self.count, self.entryAction, self.shortEMAoverLongEMA, self.stateChanged))
        self.prevMidpoint = midpoint

        if self.count > 0 and self.entryAction == 'SELL':
            logging.warn('not entering sell side yet.')
            self.count = 0
            return None, None
        if self.count == self.watchCount and self.entryAction == 'BUY' and self.watchMidpoint < midpoint:
            self.count = 0
            entryPrice = lowMidpoint if self.entryAction == 'BUY' else highMidpoint
            logging.warn('returning an entry at {} on side {}'.format(entryPrice, self.entryAction))
            return self.entryAction, entryPrice # entryAction of entry, entryPrice
        elif self.count == self.watchCount and self.entryAction == 'BUY':
            logging.warn('midpoint did not increase over lifespan of watch')
        return None, None
