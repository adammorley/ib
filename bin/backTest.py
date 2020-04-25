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
from market import order
from market import rand 

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--info', action='store_true', default=None)
parser.add_argument('--error', action='store_true', default=None)
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
if args.error is not None:
    logLevel = logging.ERROR
elif args.info is not None:
    logLevel = logging.INFO
elif args.debug is not None:
    logLevel = logging.DEBUG

ib = connect.connect(logLevel)
conf = config.getConfig(args.conf)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget)
logging.info('config %s', conf)

contract = contract.getContract(args.symbol, args.localSymbol)
qc = ib.qualifyContracts(contract)
if len(qc) < 1:
    logging.fatal('could not validate contract')
    sys.exit(1)
useRth = False if conf.buyOutsideRth else True
histBars = ib.reqHistoricalData(contract, endDateTime=args.endDate, durationStr=str(args.duration)+' D', barSizeSetting=args.tickSize, whatToShow='TRADES', useRTH=useRth, formatDate=2)
ib.sleep(1)
newBars = backtest.anotateBars(histBars)

data = {'first':None, 'second':None, 'third':None}
trade = None
positions = []
totalGainLoss = 0
totalFundsInPlay = 0
maxFundsInPlay = 0
data['first'] = backtest.getNextBar(newBars, 0)
data['second'] = backtest.getNextBar(newBars, 1)
for i in range(2, len(newBars)-1):
    if i > 3:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = backtest.getNextBar(newBars, i)

    # first, see if any positions changed
    for position in positions:
        # wonky use of executed vs amount
        closed, amount = backtest.checkPosition(data['third'], position)
        if closed:
            logging.error('closed a position: %.2f %r %s %s', amount, closed, position, data['third'])
            totalGainLoss += amount
            if totalFundsInPlay > maxFundsInPlay:
                maxFundsInPlay = totalFundsInPlay
            totalFundsInPlay -= position.buyPrice * position.config.qty
            positions.remove(position)
        # position stays, no changes

    # analyze the trade for execution
    trade = order.Analyze(data, conf)
    if trade is not None:
        logging.info('found an order: %s %s', trade, data)
        if len(positions) < trade.config.openPositions:
            position, amount = backtest.checkTradeExecution(data['third'], trade)
            # check if the trade executed
            if position is not None:
                logging.error('opened a position: %s', position)
                positions.append(position)
                totalFundsInPlay += position.buyPrice * position.config.qty
            elif position is None and amount is not None:
                logging.error('opened and closed a position in third bar')
                totalGainLoss += amount
            logging.info('totalFundsInPlay: %.2f', totalFundsInPlay)

r = 0
if args.symbol == 'ES':
    totalGainLoss=totalGainLoss*50 # es00 futures ticks are 12.5 per tick
if maxFundsInPlay > 0:
    r = totalGainLoss/maxFundsInPlay*100
logging.fatal('totalGainLoss: %.2f, maxFundsInPlay: %.2f, return: %.2f', totalGainLoss, maxFundsInPlay, r)

ib.cancelHistoricalData(histBars)
ib.sleep(1)
ib.disconnect()

sys.exit(0)
