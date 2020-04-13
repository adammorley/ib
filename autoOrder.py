#!/usr/bin/python3

import datetime
import dumper
import logging
import sys

from ib_insync import *

import argparse
#parser = argparse.ArgumentParser()
#parser.add_argument("stopPrice", type=float)
#parser.add_argument("profitPrice", type=float)
#args = parser.parse_args()
stopPrice = 2.7
profitPrice = 6

class Bar:
    open_: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 9223372036854775807.
    barSize: float = 0.0
    lineSize: float = 0.0
    color: str = 'X'

numberOfTicksInBar = 240

# get the next minute's bar
def getNextBar(t, ib):
    logging.debug('getting points every 250ms')
    bar = Bar()
    bar.open = t.marketPrice()
    for i in range(0, numberOfTicksInBar):
        m = t.marketPrice()
        if m > bar.high:
            bar.high = m
        elif m < bar.low:
            bar.low = m
        ib.sleep(0.250)
    bar.close = t.marketPrice()
    return anotateBar( cleanUpBar(bar) )

def cleanUpBar(bar):
    logging.debug('cleaning up bar')
    if bar.close < bar.low:
        bar.low = bar.close
    elif bar.close > bar.high:
        bar.high = bar.close
    return bar

def anotateBar(bar):
    bar.barSize = abs(bar.open - bar.close)
    bar.lineSize = abs(bar.high - bar.low)
    if bar.open < bar.close:
        bar.color = 'G'
    elif bar.close < bar.open:
        bar.color = 'R'
    elif bar.close == bar.open and bar.high != bar.low:
        bar.color = 'G'
    return bar

class OrderDetails:
    buyPrice: float = 0.0
    stopPrice: float = 0.0
    profitPrice: float = 0.0

def analyze(d):
    if d['first'].color == 'X' or d['second'].color == 'X' or d['third'].color == 'X':
        logging.debug('got a partial bar')
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
    stopPrice = d['second'].close - stopPrice
    profitPrice = d['third'].close + profitPrice
    logging.info('found a potential buy point, buy: %i, stop: %i, profit: %i', buyPrice, stopPrice, profitPrice)
    #if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
    if True:
        logging.debug('valid buy point, returning')
        od = OrderDetails()
        od.buyPrice = buyPrice
        od.stopPrice = stopPrice
        od.profitPrice = profitPrice
        return od
    return None

# the back testing assumes the trade is placed in the next 1 minute window or canceled.
def placeOrder(od):
    o = bracketOrder(action='BUY', quantity=100, limitPrice=od.buyPrice, takeProfitPrice=od.profitPrice, stopLossPrice=od.stopPrice, outsideRth=True)
    t = ib.placeOrder(c, o)
    ib.sleep(0)
    logging.info('placed trade')
    return t


startTime = datetime.datetime.utcnow()

util.logToConsole(logging.INFO)
ib = IB()
ib.connect("localhost", 4002, clientId=3)
ib.sleep(1)
if not ib.isConnected():
    logging.fatal('did not connect.')
    sys.exit(1)

logging.info('connected, qualifying contract')
contract = Stock('TQQQ', 'SMART', 'USD', primaryExchange='NASDAQ')
ib.qualifyContracts(contract)
ticker = ib.reqMktData(contract, '', False, False)
ib.sleep(1)

logging.info('running trade loop')
data = {'first':None, 'second':None, 'third':None}
trade = None
while datetime.datetime.utcnow() < startTime + datetime.timedelta(hours=24):
    if data['first'] is None and data['second'] is None:
        data['first'] = getNextBar(ticker, ib)
        data['second'] = getNextBar(ticker, ib)
    else:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = getNextBar(ticker, ib)
    logging.debug(dumper.dump(data))
    orderdetails = analyze(data)
    if orderdetails is not None:
        trade = placeOrder(orderdetails)
        for i in range(0, 10):
            if not trade.isDone():
                ib.sleep(0.100)
        logging.info(dumper.dump(trade))
        logging.info(ib.trades())
    else:
        logging.info('did not find a trade')

ib.cancelMktData(contract)
ib.sleep(1)
ib.disconnect()

sys.exit(0)
