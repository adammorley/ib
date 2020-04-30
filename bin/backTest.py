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
parser.add_argument('--info', action='store_true', default=None)
parser.add_argument('--conf', type=str, required=True)
parser.add_argument("--duration", default=5, type=int)
parser.add_argument("--endDate", default='', type=str)
parser.add_argument("--tickSize", default='1 min', type=str)
parser.add_argument('--symbol', required=True, type=str)
parser.add_argument('--localSymbol', type=str, default=None)
parser.add_argument('--profitTarget', default=None, type=float)
parser.add_argument('--stopTarget', default=None, type=float)
args = parser.parse_args()

ibc = connect.connect(args.debug)
if args.info:
    util.logToConsole(logging.INFO)
conf = config.getConfig(args.conf)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget)

wc = contract.wContract(ibc, args.symbol, args.localSymbol)

useRth = False if conf.buyOutsideRth else True
histBars = data.getHistData(wc=wc, ibc=ibc, barSizeStr=args.tickSize, longInterval=None, e=args.endDate, d=args.duration, t='TRADES', r=useRth, f=2, k=False)
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
    trade = order.OrderDetails(barSet.analyze(), conf, wc)
    if trade.buyPrice is not None:
        trade.config.qty = order.calculateQty(trade)
        logging.warn('found an order: %s %s', trade, barSet)
        if len(positions) < trade.config.openPositions:
            position, amount = backtest.checkTradeExecution(barSet.third, trade)
            logging.warn('position config %s', position.config)
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

ibc.cancelHistoricalData(histBars)
connect.close(ibc)

sys.exit(0)
