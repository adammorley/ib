import logging
import sys
import yaml
from os import path

def getConfig(configFile):
    if not path.isfile(configFile):
        logging.fatal('need config file')
        sys.exit(1)
    with open(configFile, 'r') as f:
        return ProcessConfig(yaml.load(f))

def overrideConfig(conf, profitTarget, stopTarget):
    if profitTarget is not None:
        conf.profitTarget = profitTarget
    if stopTarget is not None:
        conf.stopTarget = stopTarget
    return conf

class Config:
    percents: bool
    profitTarget: float
    profitPercent: float
    stopPercent: float
    stopTarget: float
    locPercent: float
    locTarget: float
    trail: bool
    qty: int
    openPositions: int
    buyOutsideRth: bool
    sellOutsideRth: bool
    byPrice: bool
    dollarAmt: float
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def ProcessConfig(conf):
    config = Config()
    config.percents = conf['percents']
    if config.percents:
        config.profitPercent = conf['profitPercent']
        config.stopPercent = conf['stopPercent']
        config.locPercent = conf['locPercent']
    else:
        config.profitTarget = conf['profitTarget']
        config.stopTarget = conf['stopTarget']
        config.locTarget = conf['locTarget']

    config.byPrice = conf['byPrice']
    if config.byPrice:
        config.dollarAmt = conf['dollarAmt']
    else:
        config.qty = conf['qty']

    config.trail = conf['trail']
    config.openPositions = conf['openPositions']
    config.buyOutsideRth = conf['buyOutsideRth']
    config.sellOutsideRth = conf['sellOutsideRth']

    return config
