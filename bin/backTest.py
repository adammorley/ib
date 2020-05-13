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

parser.add_argument("--duration", default=10, type=int)
parser.add_argument("--endDate", default='', type=str)

parser.add_argument('--shortEMA', default=15, type=int)
parser.add_argument('--longEMA', default=40, type=int)
parser.add_argument('--watchCount', default=15, type=int)
parser.add_argument('--profitTarget', default=3, type=float)
parser.add_argument('--stopTarget', default=7, type=float)
args = parser.parse_args()

def modTotals(totals):
    if conf.symbol == 'ES':
        totals['gl']=totals['gl']*50
    return totals

conf = config.getConfig(args.conf, detectorOn=True)
ibc = connect.connect(conf, args.debug)
if args.info:
    util.logToConsole(logging.INFO)
if args.error:
    util.logToConsole(logging.ERROR)
conf = config.overrideConfig(conf, args.profitTarget, args.stopTarget, args.shortEMA, args.longEMA, args.watchCount)

wc = contract.wContract(ibc, conf.symbol, conf.localSymbol)

useRth = False if conf.enterOutsideRth else True
backtestArgs = {'watchCount': args.watchCount, 'shortInterval': args.shortEMA, 'longInterval': args.longEMA, 'e': args.endDate, 'd': args.duration, 't': 'MIDPOINT', 'r': useRth, 'f': 2, 'k': False}
dataStore, dataStream = detector.setupData(wc, conf, backtestArgs)

if conf.detector == 'threeBarPattern':
    dataStream = backtest.anotateBars(dataStream)

if args.single:
    totals = backtest.backtest(wc, dataStream, dataStore, conf)
    print(modTotals(totals))
    sys.exit(0)
#for p in [1, 5, 10, 14, 30, 60]:
for p in [1, 5, 7]:
    #for lI in [20, 40, 60, 120, 200]:
    for lI in [20]:
        #for sI in [5, 15, 30, 50]:
        for sI in [5]:
            if sI > lI:
                continue
            #for w in [5, 15, 30]:
            for w in [5]:
                #for sT in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 20, 25]:
                for sT in [0.25]:
                    #for pT in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 20, 30]:
                    for pT in [1]:
                        ID = 'lI:'+str(lI)+', sI:'+str(sI)+', w:'+str(w)+', sT:'+str(sT)+', pT:'+str(pT)+', pD:'+str(p)
                        #logging.error('running %s', ID)
                        conf.profitPercent = pT
                        conf.stopPercent = sT
                        if conf.detector == 'emaCrossover':
                            dataStore = detector.EMA(conf.barSizeStr, wc, sI, lI, w)
                            dataStore.backTest = True
                            dataStore.byPeriod = p
                            dataStore.calcInitEMAs(dataStream)
                        totals = modTotals( backtest.backtest(wc, dataStream, dataStore, conf, p) )
                        r = totals['gl']/totals['mf']*100 if totals['mf'] > 0 else 0
                        if totals['gl'] > 0:
                            er = int(totals['gl']/totals['op'])
                            logging.error(str(ID)+'; gl:'+str(totals['gl'])+', op:'+str(totals['op'])+', er:'+str(er) +', lo:'+str(totals['lo']))

#backtest.backtest(wc, dataStream, dataStore, conf)
## are any positions left open?
##logging.warn('checking for any leftover positions')
##lastClose = dataStream[len(dataStream)-1].close
##for position in positions:
#    #totals['gl'] += lastClose - position.entryOrder.lmtPrice   
connect.close(ibc)

sys.exit(0)
