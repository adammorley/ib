import logging
import sys

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
    outsideRth: bool
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

    config.trail = conf['trail']
    config.qty = conf['qty']
    config.openPositions = conf['openPositions']
    config.outsideRth = conf['outsideRth']

    return config
