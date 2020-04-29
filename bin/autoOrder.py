#!/usr/bin/python3

import datetime
import logging
import sys

from ib_insync import *

sys.path.append(r'.')
from market import bars
from market import config
from market import connect
from market import contract
from market import data
from market import detector
from market import order
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--conf', type=str, required=True)
parser.add_argument('--symbol', type=str, required=True)
parser.add_argument('--localSymbol', type=str)
parser.add_argument('--short', type=int) # for ema detector, short moving avg
parser.add_argument('--long', type=int) # for ema detector, long moving avg
parser.add_argument('--prod', action='store_true', default=None)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

def isMaxQty(p, conf):
    if conf.byPrice:
        # super wonky: avg cost is avg cost per share
        # .position is share count
        # dollarAmt is the max we'll spend
        # openPositions is the number of amounts
        #  $25 * 4 sh >= $500 * 2
        return p.avgCost * p.position >= conf.dollarAmt * conf.openPositions
    else:
        return p.position >= conf.qty * conf.openPositions

startTime = datetime.datetime.utcnow()

ibc = connect.connect(args.debug, args.prod)
conf = config.getConfig(args.conf)

if args.localSymbol:
    c = contract.getContract(args.symbol, args.localSymbol)
else:
    c = contract.getContract(args.symbol, None)
contract.qualify(c, ibc)

dataStore = None
dataStream = None
flag = False
count = 0
if conf.detector == 'threeBarPattern':
    dataStream = data.getTicker(c, ibc)
    dataStore = bars.BarSet()
elif conf.detector == 'emaCrossover':
    dataStream = data.getHistData(c, ibc)
    curPrice = len(histData) - 2
    emaShort = data.EMA(histData[curPrice], data.SMA(args.short, histData), args.short)
    emaLong = data.EMA(histData[curPrice], data.SMA(args.long, histData), args.long)
    dataStore = detector.EMA(emaShort, emaLong, args.short, args.long)
else:
    raise RuntimeError('do not know what to do!')

# what we really want is to extract the "I detected a reason to buy contract n at bar y with reuqirements z"
# and add the es one as well.
logging.warn('running trade loop for %s...', c.symbol)
while datetime.datetime.utcnow() < startTime + datetime.timedelta(hours=20):
    buyPrice = None
    if conf.detector == 'threeBarPattern':
        buyPrice = detector.threeBarPattern(dataStore, dataStream, ibc.sleep)
    elif conf.detector == 'emaCrossover':
        buyPrice = dataStore.checkForBuy(dataStream, ib.sleep)

    orderDetails = None
    if buyPrice is not None:
        try:
            orderDetails = order.OrderDetails(buyPrice, conf, c)
        except FloatingPointError as e:
            logging.debug('got a NaN %s', e)

    if orderDetails is not None:
        positions = ibc.positions()
        ibc.sleep(0)
        makeTrade = True
        for p in positions:
            if p.contract == c and isMaxQty(p, conf):
                logging.warn('passing on trade as max positions already open')
                makeTrade = False

        if makeTrade:
            orders = order.CreateBracketOrder(orderDetails)
            trades = trade.PlaceBracketTrade(orders, orderDetails, ibc)
            trade.CheckTradeExecution(trades, orderDetails)
            logging.debug(trades)

connect.close(ibc, c)
sys.exit(0)
