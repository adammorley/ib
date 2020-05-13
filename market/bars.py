import logging
import math

from market import fatal

class Bar:
    open_: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 92233720368547758.0
    barSize: float = 0.0
    lineSize: float = 0.0
    color: str = 'X'

    # just create a bar, will update
    def __init__(self, init):
        self.open = init
        self.close = init
        self.high = init
        self.low = init

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def cleanUp(self):
        logging.debug('cleaning up bar %s', self)
        if self.close < self.low:
            self.low = self.close
        elif self.close > self.high:
            self.high = self.close

    def anotate(self): # used for three-bar pattern detection
        self.barSize = abs(self.open - self.close)
        self.lineSize = abs(self.high - self.low)
        if self.open < self.close:
            self.color = 'G'
        elif self.close < self.open:
            self.color = 'R'
        elif self.close == self.open and self.high != self.low:
            self.color = 'G'
        elif math.isnan(self.close) or math.isnan(self.open):
            fatal.errorAndExit('got a self with NaN: {}'.format(self))

class BarSet:
    first: Bar = None
    second: Bar = None
    third: Bar = None
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def analyze(self):
        entryPrice = None
        if self.first.color == 'X' or self.second.color == 'X' or self.third.color == 'X':
            logging.debug('got a partial bar')
        #FIXME: the bar size testing seems to have a large impact on not entering, to the detriment of the return
        elif not self.first.color == 'G' and not self.second.color == 'R' and not self.third.color == 'G' and not self.second.barSize < 0.3 * self.first.barSize and not self.second.barSize < 0.5 * self.third.barSize and not self.third.barSize > self.second.barSize:
            entryPrice = None
        else:
            entryPrice = self.third.close
            if math.isnan(entryPrice):
                fatal.errorAndExit('got floating point which is NaN {} {}'.format(entryPrice, self.third))
        
            logging.info('found a potential entry point: %d', entryPrice)
        return entryPrice
