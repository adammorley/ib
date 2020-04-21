#!/usr/bin/python3

import collections
import dumper
import logging
import sys
import yaml

from ib_insync import *

from market import bars
from market import config
from market import order
from market import rand 

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument("--duration", default=5, type=int)
parser.add_argument("--endDate", default='', type=str)
parser.add_argument("--tickSize", default='1 min', type=str)
parser.add_argument('--symbol', required=True, type=str)
parser.add_argument('--conId')
parser.add_argument('--profitTarget', default=None, type=float)
parser.add_argument('--stopTarget', default=None, type=float)
args = parser.parse_args()

def getConfig(symbol):
    with open('conf/' + symbol, 'r') as f:
        return config.ProcessConfig(yaml.load(f))

def overrideConfig(conf):
    if args.profitTarget is not None:
        conf.profitTarget = args.profitTarget
    if args.stopTarget is not None:
        conf.stopTarget = args.stopTarget
    return conf

def contractLookup(symbol, conId):
    if symbol == 'TQQQ':
        return Stock('TQQQ', 'SMART', 'USD', primaryExchange='NASDAQ')
    elif symbol == 'ES':
        return Contract(symbol='ES', exchange='GLOBEX', currency='USD', conId=conId)
    else:
        logging.fatal('unsupported contract')
        sys.exit(1)


def anotateBars(histBars):
    newBars = []
    for i in range(0, len(histBars)):
        newBars.append(makeBar(histBars[i]))
        newBars[i] = bars.AnotateBar(newBars[i])
    return newBars

def makeBar(histBar):
    bar = bars.Bar()
    bar.open = histBar.open
    bar.close = histBar.close
    bar.high = histBar.high
    bar.low = histBar.low
    return bar

def getNextBar(newBars, index):
    return newBars[index]

# only used to check the third bar for if the order bought/sold in the third bar during "blur"
def checkTradeExecution(bar, trade):
    if trade.buyPrice <= bar.high and trade.buyPrice - trade.config.stopTarget >= bar.low:
        return None, (-1 * trade.config.stopTarget)
    else:
        return trade, None

# check if a "position" (represented by a fictitious order) changed in the bar
# returns orderDetails and amount
def checkPosition(bar, position):
    amount, executed = checkStopProfit(position, bar)
    if executed == False:
        # order became a position, say so
        return False, None
    elif executed == True or executed == None:
        # position closed, return amount
        return True, amount
    else:
        logging.error('problem with position checking %s %s', position, bar)
        return None, None

# orderDetails represents a ficitious order which:
#   fails to execute
#   opens and closes really fast (inside the next bar)
#   becomes a "position" representing shares held
# returns amount or None (error condition)
# need another value which is "continue"
# returns
#       True|False as to whether the trade executed
#       amount neg or pos (loss/gain) or None if unknown
def checkStopProfit(position, bar):
    amount = None
    executed = None
    # executed at stop price
    if position.buyPrice - position.config.stopTarget >= bar.low and position.buyPrice + position.config.profitTarget > bar.high:
        amount = (-1 * position.config.stopTarget) * position.config.qty
        logging.info('closing position at a loss: %.2f %s %s', amount, position, bar)
        executed = True
    # executed at profit price
    elif position.buyPrice - position.config.stopTarget < bar.low and position.buyPrice + position.config.profitTarget <= bar.high:
        amount = position.config.profitTarget * position.config.qty
        logging.info('closing position at a gain: %.2f %s %s', amount, position, bar)
        executed = True
    # did not execute, no delta, stays as a position
    elif position.buyPrice - position.config.stopTarget < bar.low and position.buyPrice + position.config.profitTarget > bar.high:
        logging.info('not closing a position: %s, %s', position, bar)
        executed = False
        amount = None
    # unknown execution, assume loss
    elif position.buyPrice - position.config.stopTarget >= bar.low and position.buyPrice + position.config.profitTarget <= bar.high:
        logging.info('wonky: closing position: %s', position)
        executed = None
        amount = (-1 * position.config.stopTarget) * position.config.qty
    else:
        logging.fatal('unhandled %s %s', position, bar)
    return amount, executed

if args.debug is not None:
    util.logToConsole(logging.DEBUG)
else:
    util.logToConsole(logging.FATAL)

conf = getConfig(args.symbol)
conf = overrideConfig(conf)

ib = IB()
ib.connect("localhost", 4002, clientId=rand.Int())

contract = contractLookup(args.symbol, args.conId)
qc = ib.qualifyContracts(contract)
if len(qc) < 1:
    logging.fatal('could not validate contract')
    sys.exit(1)
useRth = False if conf.outsideRth else True
histBars = ib.reqHistoricalData(contract, endDateTime=args.endDate, durationStr=str(args.duration)+' D', barSizeSetting=args.tickSize, whatToShow='TRADES', useRTH=useRth, formatDate=1)
ib.sleep(1)
newBars = anotateBars(histBars)

data = {'first':None, 'second':None, 'third':None}
trade = None
positions = []
totalGainLoss = 0
totalFundsInPlay = 0
maxFundsInPlay = 0
data['first'] = getNextBar(newBars, 0)
data['second'] = getNextBar(newBars, 1)
for i in range(2, len(newBars)-1):
    if i > 3:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = getNextBar(newBars, i)

    # first, see if any positions changed
    for position in positions:
        # wonky use of executed vs amount
        closed, amount = checkPosition(data['third'], position)
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
            position, amount = checkTradeExecution(data['third'], trade)
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
