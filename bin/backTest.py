#!/usr/bin/python3

import collections
import dumper
import logging
import sys
import yaml

from ib_insync import *

sys.path.append(r'.')

from market import backtest
from market import bars
from market import config
from market import connect
from market import contract
from market import data
from market import order
from market import rand 

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--conf', type=str, required=True)
parser.add_argument("--duration", default=5, type=int)
parser.add_argument("--endDate", default='', type=str)
parser.add_argument("--tickSize", default='1 min', type=str)
parser.add_argument('--symbol', required=True, type=str)
parser.add_argument('--localSymbol', type=str)
parser.add_argument('--profitTarget', default=None, type=float)
parser.add_argument('--stopTarget', default=None, type=float)
args = parser.parse_args()

logLevel = logging.FATAL
if args.debug is not None:
    logLevel = logging.DEBUG

ib = connect.connect(logLevel)
conf = config.getConfig(args.conf)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget)

c = contract.getContract(args.symbol, args.localSymbol)
contract.qualify(c, ibc)

useRth = False if conf.buyOutsideRth else True
histBars = ib.reqHistoricalData(c, endDateTime=args.endDate, durationStr=str(args.duration)+' D', barSizeSetting=args.tickSize, whatToShow='TRADES', useRTH=useRth, formatDate=2)
ib.sleep(1)
newBars = backtest.anotateBars(histBars)

barSet = bars.BarSet()
trade = None
positions = []
totalGainLoss = 0
totalFundsInPlay = 0
maxFundsInPlay = 0
barSet.first = backtest.getNextBar(newBars, 0)
barSet.second = backtest.getNextBar(newBars, 1)
for i in range(2, len(newBars)-1):
    if i > 3:
        barSet.first = barSet.second
        barSet.second = barSet.third
    barSet.third = backtest.getNextBar(newBars, i)

    # first, see if any positions changed
    for position in positions:
        # wonky use of executed vs amount
        closed, amount = backtest.checkPosition(barSet.third, position)
        if closed:
            logging.warn('closed a position: %.2f %r %s %s', amount, closed, position, barSet.third)
            totalGainLoss += amount
            if totalFundsInPlay > maxFundsInPlay:
                maxFundsInPlay = totalFundsInPlay
            totalFundsInPlay -= position.buyPrice * position.config.qty
            positions.remove(position)
        # position stays, no changes

    # analyze the trade for execution
    trade = order.OrderDetails(barSet.analyze(), conf, c)
    if trade.buyPrice is not None:
        logging.warn('found an order: %s %s', trade, barSet)
        if len(positions) < trade.config.openPositions:
            position, amount = backtest.checkTradeExecution(barSet.third, trade)
            # check if the trade executed
            if position is not None:
                logging.warn('opened a position: %s', position)
                positions.append(position)
                totalFundsInPlay += position.buyPrice * position.config.qty
            elif position is None and amount is not None:
                logging.warn('opened and closed a position in third bar')
                totalGainLoss += amount
            logging.debug('totalFundsInPlay: %.2f', totalFundsInPlay)

r = 0
if args.symbol == 'ES':
    totalGainLoss=totalGainLoss*50 # es00 futures ticks are 12.5 per tick
if maxFundsInPlay > 0:
    r = totalGainLoss/maxFundsInPlay*100
logging.warn('totalGainLoss: %.2f, maxFundsInPlay: %.2f, return: %.2f', totalGainLoss, maxFundsInPlay, r)

ib.cancelHistoricalData(histBars)
ib.sleep(1)
ib.disconnect()

sys.exit(0)
