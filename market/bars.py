import logging

class Bar:
    open_: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 9223372036854775807.
    barSize: float = 0.0
    lineSize: float = 0.0
    color: str = 'X'
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

numberOfTicksInBar = 240
sleepSecs = 0.250

# get the next minute's bar
def GetNextBar(tick, sleepFunc):
    logging.debug('getting points every 250ms')
    bar = Bar()
    bar.open = tick.marketPrice()
    bar.close = bar.open
    bar.low = bar.open
    bar.high = bar.open
    for i in range(0, numberOfTicksInBar):
        m = tick.marketPrice()
        if m > bar.high:
            bar.high = m
        elif m < bar.low:
            bar.low = m
        sleepFunc(sleepSecs)
    bar.close = tick.marketPrice()
    return AnotateBar( CleanUpBar(bar) )

def CleanUpBar(bar):
    logging.debug('cleaning up bar')
    if bar.close < bar.low:
        bar.low = bar.close
    elif bar.close > bar.high:
        bar.high = bar.close
    return bar

def AnotateBar(bar):
    bar.barSize = abs(bar.open - bar.close)
    bar.lineSize = abs(bar.high - bar.low)
    if bar.open < bar.close:
        bar.color = 'G'
    elif bar.close < bar.open:
        bar.color = 'R'
    elif bar.close == bar.open and bar.high != bar.low:
        bar.color = 'G'
    else:
        logging.debug('got funny bar')
        bar.color = 'X'
    return bar
