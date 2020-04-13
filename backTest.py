#!/usr/bin/python3

import collections
import dumper
import logging
import sys

from ib_insync import *

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("stopPrice", type=float)
parser.add_argument("profitPrice", type=float)
parser.add_argument("duration", type=int)
parser.add_argument("endDate")
args = parser.parse_args()

def anotateBars(bars):
    for i in range(0, len(bars)):
        bars[i] = anotateBar(bars[i])
    return bars

def anotateBar(bar):
    bar.barSize = abs(bar.open - bar.close)
    bar.lineSize = abs(bar.high - bar.low)
    if bar.open < bar.close:
        bar.color = 'G'
    elif bar.close < bar.open:
        bar.color = 'R'
    elif bar.close == bar.open and bar.high != bar.low:
        bar.color = 'G'
    else:
        bar.color = 'X'
    return bar


#def analyze(d, bar):
def analyze(d):
    if d['first'].color == 'X' or d['second'].color == 'X' or d['third'].color == 'X':
        logging.error('got a partial bar')
        return None
    if not d['first'].color == 'G':
        return None
    if not d['second'].color == 'R':
        return None
    if not d['third'].color == 'G':
        return None
    if not d['second'].barSize < 0.2 * d['first'].barSize:
        return None

    #buyPrice = d['third'].open + 0.5 * d['third'].barSize
    #buyPrice = bar.open + bar.barSize * 0.5 # simulating buying at market in next interval
    buyPrice = d['third'].close
    stopPrice = d['second'].close - args.stopPrice
    profitPrice = d['third'].close + args.profitPrice
    logging.info('found a potential buy point, buy: %i, stop: %i, profit: %i', buyPrice, stopPrice, profitPrice)
    #if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
    if True:
        logging.info('valid buy point, returning')
        return {'buyPrice': buyPrice, 'stopPrice': stopPrice, 'profitPrice': profitPrice }
    return None

def getNextBar(bars, index):
    return bars[index]

# returns true/false on execution and potential gain/loss
# returns position and gain/loss
def checkTradeExecution(bar, trade):
    if trade['buyPrice'] < bar.high and trade['buyPrice'] > bar.low:
        closed, amount = checkPosition(bar, trade)
        if not closed:
            return trade, None
        elif closed:
            return None, amount
        else:
            logging.error('problem with trade execution: %s %s', bar, trade)
            logging.error(bar, trade)
    else:
        return None, None

# check if a position changed in the bar
# returns position and amount
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

#position is a type: purchasePrice, stopPrice, profitPrice
# returns amount or None (error condition)
# need another value which is "continue"
# returns
#       True|False as to whether the trade executed
#       amount neg or pos (loss/gain) or None if unknown
def checkStopProfit(position, bar):
    amount = None
    executed = None
    # executed at stop price
    if position['stopPrice'] >= bar.low and position['profitPrice'] > bar.high:
        amount = position['stopPrice'] - position['buyPrice']
        logging.info('closing position at a loss: %i %s %s', amount, position, bar)
        executed = True
    # executed at profit price
    elif position['stopPrice'] < bar.low and position['profitPrice'] <= bar.high:
        amount = position['profitPrice'] - position['buyPrice']
        logging.info('closing position at a gain: %i %s %s', amount, position, bar)
        executed = True
    # did not execute, no delta, stays as a position
    elif position['stopPrice'] < bar.low and position['profitPrice'] > bar.high:
        logging.info('not closing a position: %s, %s', position, bar)
        executed = False
        amount = None
    # unknown execution, assume loss
    elif position['stopPrice'] > bar.low and position['profitPrice'] < bar.high:
        logging.info('wonky: closing position: %s', position)
        executed = None
        amount = position['stopPrice'] - position['buyPrice']
    else:
        logging.error('unhandled %s %s', position, bar)
    return amount, executed

util.logToConsole(logging.FATAL)
ib = IB()
ib.connect("localhost", 4002, clientId=3)

contract = Stock('TQQQ', 'SMART', 'USD', primaryExchange='NASDAQ')
#contract = Future('ES', '202006', 'GLOBEX')
ib.qualifyContracts(contract)
bars = ib.reqHistoricalData(contract, endDateTime=args.endDate, durationStr=str(args.duration)+' D', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=1)
ib.sleep(1)
anotateBars(bars)

data = {'first':None, 'second':None, 'third':None}
trade = None
positions = []
totalGainLoss = 0
totalFundsInPlay = 0
maxFundsInPlay = 0
data['first'] = getNextBar(bars, 0)
data['second'] = getNextBar(bars, 1)
for i in range(2, len(bars)-1):
    if i > 3:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = getNextBar(bars, i)

    # first, see if any positions changed
    for position in positions:
        # wonky use of executed vs amount
        closed, amount = checkPosition(data['third'], position)
        if closed:
            logging.error('closed a position: %i %s %s', amount, position, data['third'])
            totalGainLoss += amount
            totalFundsInPlay -= position['buyPrice']
            if totalFundsInPlay > maxFundsInPlay:
                maxFundsInPlay = totalFundsInPlay
            positions.remove(position)
        # position stays, no changes

    # analyze the trade for execution
    trade = analyze(data)
    #trade = analyze(data)
    if trade is not None:
        logging.info('found a trade: %s %s', trade, data)
        position, amount = checkTradeExecution(data['third'], trade)
        # check if the trade executed
        if position is not None:
            logging.error('opened a position: %s', position)
            positions.append(position)
            totalFundsInPlay += position['buyPrice']
        elif position is None and amount is not None:
            totalGainLoss += amount
        logging.info('totalFundsInPlay: %i', totalFundsInPlay)

r = 0
if maxFundsInPlay > 0:
    r = totalGainLoss/maxFundsInPlay*100
logging.fatal('totalGainLoss: %i, maxFundsInPlay: %i, return: %i', totalGainLoss, maxFundsInPlay, r)

ib.cancelHistoricalData(bars)
ib.sleep(1)
ib.disconnect()

sys.exit(0)
