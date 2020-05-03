import logging
import yaml

def getConfig(configFile, detectorOn=None):
    with open(configFile, 'r') as f:
        return ProcessConfig(yaml.load(f), detectorOn)

def overrideConfig(conf, profitTarget=None, stopTarget=None, shortEMA=None, longEMA=None, watchCount=None):
    if profitTarget is not None:
        conf.profitTarget = profitTarget
    if stopTarget is not None:
        conf.stopTarget = stopTarget
    if shortEMA is not None:
        conf.shortEMA = shortEMA
    if longEMA is not None:
        conf.longEMA = longEMA
    if watchCount is not None:
        conf.watchCount = watchCount
    return conf

class Config:
    symbol: str = None
    localSymbol: str = None
    percents: bool
    profitTarget: float
    profitPercent: float
    stopPercent: float
    stopTarget: float
    dayOrder: bool
    dayPercent: float
    dayTarget: float
    trail: bool
    qty: int
    openPositions: int
    buyOutsideRth: bool
    sellOutsideRth: bool
    byPrice: bool
    dollarAmt: float
    detector: str
    barSizeStr: str
    longEMA: int
    shortEMA: int
    watchCount: int
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def ProcessConfig(conf, detectorOn=None):
    config = Config()

    config.symbol = conf['symbol']
    if config.symbol == 'ES': # FIXME: make this better, maybe via assert on contract?
        config.localSymbol = conf['localSymbol']
    config.percents = conf['percents']
    config.dayOrder = conf['dayOrder']
    config.byPrice = conf['byPrice']

    if config.byPrice:
        config.dollarAmt = conf['dollarAmt']
    else:
        config.qty = conf['qty']

    if config.percents:
        config.profitPercent = conf['profitPercent']
        config.stopPercent = conf['stopPercent']
        if config.dayOrder:
            config.dayPercent = conf['dayPercent']
    else:
        config.profitTarget = conf['profitTarget']
        config.stopTarget = conf['stopTarget']
        if config.dayOrder:
            config.dayTarget = conf['dayTarget']

    config.trail = conf['trail']
    config.openPositions = conf['openPositions']
    config.buyOutsideRth = conf['buyOutsideRth']
    config.sellOutsideRth = conf['sellOutsideRth']

    if detectorOn:
        config.detector = conf['detector']
        config.barSizeStr = conf['barSizeStr']
        if config.detector == 'emaCrossover':
            config.shortEMA = conf['shortEMA']
            config.longEMA = conf['longEMA']
            config.watchCount = conf['watchCount']

    logging.warn('config %s', conf)
    return config
