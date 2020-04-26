import logging

class Bar:
    open_: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 9223372036854775807.
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

    def anotate(self):
        self.selfSize = abs(self.open - self.close)
        self.lineSize = abs(self.high - self.low)
        if self.open < self.close:
            self.color = 'G'
        elif self.close < self.open:
            self.color = 'R'
        elif self.close == self.open and self.high != self.low:
            self.color = 'G'
        elif self.close != self.close and self.open != self.open:
            raise FloatingPointError('got a self with NaN: %s', self)
        else:
            self.color = 'X'
            raise Exception('unhandled self type: %s', self)

numberOfTicksInBar = 240
sleepSecs = 0.250

# get the next minute's bar
def GetNextBar(ticker, sleepFunc):
    logging.debug('getting points every 250ms')
    bar = Bar(ticker.marketPrice())
    for i in range(0, numberOfTicksInBar):
        m = ticker.marketPrice()
        if m > bar.high:
            bar.high = m
        elif m < bar.low:
            bar.low = m
        sleepFunc(sleepSecs)
    bar.close = ticker.marketPrice()
    return bar.cleanUp().anotate()

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
        if self.first.color == 'X' or self.second.color == 'X' or self.third.color == 'X':
            logging.debug('got a partial bar')
            return None
        if not self.first.color == 'G':
            return None
        if not self.second.color == 'R':
            return None
        if not self.third.color == 'G':
            return None
        if not self.second.barSize < 0.2 * self.first.barSize:
            return None
        if not self.second.barSize < 0.5 * self.third.barSize:
            return None
        if not self.third.barSize > self.second.barSize:
            return None
    
        buyPrice = self.third.close
        if buyPrice != buyPrice:
            raise FloatingPointError('got floating point which is NaN')
    
        logging.debug('found a potential buy point: %d, %s', buyPrice)
        return buyPrice
