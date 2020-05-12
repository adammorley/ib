#!/usr/bin/python3

import collections
import dumper
import logging
import sys
import yaml

from ib_insync import *

sys.path.append(r'/home/adam/ib')
from market import backtest
from market import bars
from market import config
from market import connect
from market import contract
from market import data
from market import detector
from market import fatal
from market import order
from market import rand 

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--single', action='store_true', default=None)
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--info', action='store_true', default=None)
parser.add_argument('--error', action='store_true', default=None)
parser.add_argument('--conf', type=str, required=True)

parser.add_argument("--duration", default=60, type=int)
parser.add_argument("--endDate", default='', type=str)

parser.add_argument('--shortEMA', default=None, type=int)
parser.add_argument('--longEMA', default=None, type=int)
parser.add_argument('--watchCount', default=None, type=int)
parser.add_argument('--profitTarget', default=None, type=float)
parser.add_argument('--stopTarget', default=None, type=float)
args = parser.parse_args()

def updateBarSet(newBars, i, dataStore):
    if i > 3:
        dataStore.first = dataStore.second
        dataStore.second = dataStore.third
    dataStore.third = backtest.getNextBar(newBars, i)
    return dataStore

def modTotals(totals):
    if conf.symbol == 'ES':
        totals['gl']=totals['gl']*50
    return totals

ibc = connect.connect(args.debug)
if args.info:
    util.logToConsole(logging.INFO)
if args.error:
    util.logToConsole(logging.ERROR)
conf = config.getConfig(args.conf, detectorOn=True)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget, args.shortEMA, args.longEMA, args.watchCount)

wc = contract.wContract(ibc, conf.symbol, conf.localSymbol)

useRth = False if conf.buyOutsideRth else True
backtestArgs = {'watchCount': args.watchCount, 'shortInterval': args.short, 'longInterval': args.long, 'e': args.endDate, 'd': args.duration, 't': 'TRADES', 'r': useRth, 'f': 2, 'k': False}
dataStore, dataStream = detector.setupData(ibc, wc, conf, backtestArgs)

newBars = None
if conf.detector == 'threeBarPattern':
    b = len(dataStream)
    dataStream = backtest.anotateBars(dataStream)
    if len(dataStream) != b:
        fatal.errorAndExit('these should match.')
    dataStore.first = backtest.getNextBar(dataStream, 0)
    dataStore.second = backtest.getNextBar(dataStream, 1)

if args.single:
    totals = backtest.backtest(wc, dataStream, dataStore, conf)
    print(modTotals(totals))
    sys.exit(0)
for p in [1, 5, 10, 14, 30, 60]:
        for lI in [10, 20, 40, 60, 120, 200]:
            for sI in [5, 15, 30, 45, 50]:
                if sI > lI:
                    continue
                for w in [5, 15, 30, 60]:
                    for sT in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 20, 25]:
                        for pT in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 20, 30]:
                            ID = 'lI:'+str(lI)+', sI:'+str(sI)+', w:'+str(w)+', sT:'+str(sT)+', pT:'+str(pT)
                            logging.error('running %s', ID)
                            conf.profitTarget = pT
                            conf.stopTarget = sT
                            dataStore = detector.EMA(conf.barSizeStr, wc, sI, lI, w)
                            dataStore.backTest = True
                            dataStore.byPeriod = p
                            dataStore.calcInitEMAs(dataStream)
                            totals = modTotals( backtest.backtest(wc, dataStream, dataStore, conf) )
                            r = totals['gl']/totals['mf']*100 if totals['mf'] > 0 else 0
                            print(str(ID) + ' ' + str(p) + ':' + str(totals['gl']))

#backtest.backtest(wc, dataStream, dataStore, conf)
## are any positions left open?
##logging.warn('checking for any leftover positions')
##lastClose = dataStream[len(dataStream)-1].close
##for position in positions:
#    #totals['gl'] += lastClose - position.buyOrder.lmtPrice   
connect.close(ibc)

sys.exit(0)
