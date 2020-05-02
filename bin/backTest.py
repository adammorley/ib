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
from market import detector
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

parser.add_argument('--symbol', required=True, type=str)
parser.add_argument('--localSymbol', type=str, default=None)

parser.add_argument('--short', default=None, type=int) # for ema detector, short moving avg
parser.add_argument('--long', default=None, type=int) # for ema detector, long moving avg
parser.add_argument('--watchCount', default=None, type=int) # for ema detector
parser.add_argument('--profitTarget', default=None, type=float)
parser.add_argument('--stopTarget', default=None, type=float)
args = parser.parse_args()

def updateBarSet(newBars, i, dataStore):
    if i > 3:
        dataStore.first = dataStore.second
        dataStore.second = dataStore.third
    dataStore.third = backtest.getNextBar(newBars, i)
    return dataStore

ibc = connect.connect(args.debug)
if args.info:
    util.logToConsole(logging.INFO)
if args.error:
    util.logToConsole(logging.ERROR)
conf = config.getConfig(args.conf, detectorOn=True)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget)

wc = contract.wContract(ibc, args.symbol, args.localSymbol)

useRth = False if conf.buyOutsideRth else True
backtestArgs = {'watchCount': args.watchCount, 'shortInterval': args.short, 'longInterval': args.long, 'e': args.endDate, 'd': args.duration, 't': 'TRADES', 'r': useRth, 'f': 2, 'k': False}
dataStore, dataStream = detector.setupData(ibc, wc, conf, backtestArgs)

newBars = None
if conf.detector == 'threeBarPattern':
    b = len(dataStream)
    dataStream = backtest.anotateBars(dataStream)
    if len(dataStream) != b:
        raise RuntimeError('these should match.')
    dataStore.first = backtest.getNextBar(dataStream, 0)
    dataStore.second = backtest.getNextBar(dataStream, 1)

positions = []
totals = {'gl': 0, 'tf': 0, 'mf': 0}
startIndex = None
# which data point in the dataStream/bar set to evaluate on this round about buy or not
if conf.detector == 'threeBarPattern':
    startIndex = 2
elif conf.detector == 'emaCrossover':
    # we just stored (at init) the last EMA calculated, eg we are examining curClosePriceIndex
    startIndex = dataStore.curEmaIndex + 1

for i in range(startIndex, len(dataStream)-1):
    if conf.detector == 'threeBarPattern':
        dataStore = updateBarSet(dataStream, i, dataStore)

    # first, see if any positions changed
    logging.info('number of positions open: {}'.format(len(positions)))
    positions, totals = backtest.checkPositions(wc, positions, conf, dataStore, dataStream, i, totals)

    # see if we calculated a buyPrice
    buyPrice = None
    if conf.detector == 'threeBarPattern':
        buyPrice = dataStore.analyze()
    elif conf.detector == 'emaCrossover':
        buyPrice = dataStore.checkForBuy(dataStream)

    if buyPrice is not None:
        od = order.OrderDetails(buyPrice, conf, wc)
        od.config.qty = order.calculateQty(od)
        logging.warn('found an order: %s %s', od, dataStore)
        if len(positions) < od.config.openPositions:
            # checking whether the position opened and closed in the same bar
            amount = None
            orders = order.CreateBracketOrder(od)
            # need to use real values (not offsets) for position checker
            if orders.stopOrder.orderType == 'TRAIL': # have to store for position tracking
                if orderDetails.config.stopPercent:
                    orders.stopOrder.auxPrice = order.Round( orders.buyOrder.lmtPrice *(100.0 - orders.stopOrder.trailingPercent)/100.0, od.wContract.priceIncrement)
                elif orderDetails.config.stopTarget:
                    orders.stopOrder.auxPrice = orders.buyOrder.lmtPrice - orderDetails.config.stopTarget
            if conf.detector == 'threeBarPattern':
                orders, amount = backtest.checkTradeExecution(dataStore.third, orders)
            elif conf.detector == 'emaCrossover':
                orders, amount = backtest.checkTradeExecution(dataStream[dataStore.curIndex], orders)
            logging.warn('position config %s', od.config)
            # check if the trade executed
            if orders is not None:
                logging.warn('opened a position: %s', orders)
                positions.append(orders)
                totals['tf'] += orders.buyOrder.lmtPrice * orders.buyOrder.totalQuantity
            elif orders is None and amount is not None:
                logging.warn('opened and closed a position in third bar')
                totals['gl'] += amount
            logging.debug('totalFundsInPlay: %.2f', totals['tf'])

# are any positions left open?
#logging.warn('checking for any leftover positions')
#lastClose = dataStream[len(dataStream)-1].close
#for position in positions:
    #totals['gl'] += lastClose - position.buyOrder.lmtPrice   

r = 0
if args.symbol == 'ES':
    totals['gl']=totals['gl']*50
if totals['mf'] > 0:
    r = totals['gl']/totals['mf']*100
logging.error('totalGainLoss: %.2f, maxFundsInPlay: %.2f, return: %.2f', totals['gl'], totals['mf'], r)

connect.close(ibc)

sys.exit(0)
