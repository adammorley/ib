#!/usr/bin/python3

import collections
import dumper
import logging
import sys

from ib_insync import *

# pass in a ticker, will get the 60 second bars
# FIXME: split analysis of data from fetch
def getNextBar(t, ib):
    logging.info('getting points every 250ms')
    d = { 'open': 0, 'close': 0, 'high': 0, 'low': 9223372036854775807, 'barSize': 0, 'lineSize': 0, 'color': 'X' }
    d['open'] = t.marketPrice()
    for i in range(0, 20):
        m = t.marketPrice()
        if m > d['high']:
            d['high'] = m
        elif m < d['low']:
            d['low'] = m
        ib.sleep(0.250)
    d['close'] = t.marketPrice()
    # FIXME: add unit test with high/low points outside bounds
    logging.info('calculating a bar')
    if d['close'] < d['low']:
        d['low'] = d['close']
    elif d['close'] > d['high']:
        d['high'] = d['close']
    d['barSize'] = abs(d['open'] - d['close'])
    d['lineSize'] = abs(d['high'] - d['low'])
    if d['close'] < d['open']:
        d['color']  = 'R'
    elif d['open'] < d['close']:
        d['color'] = 'G'
    return d

def analyze(d):
    if d['first']['color'] == 'X' or d['second']['color'] == 'X' or d['third']['color'] == 'X':
        logging.info('got a partial bar')
        logging.info(dumper.dump(d))
        return None
    if not d['first']['color'] == 'G':
        return None
    if not d['second']['color'] == 'R':
        return None
    if not d['third']['color'] == 'G':
        return None
    if not d['second']['barSize'] < 0.2 * d['first']['barSize']:
        return None
    if not d['third']['barSize'] > d['second']['barSize']:
        return None
    if not d['second']['lineSize'] < 2 * d['second']['barSize']:
        return None

    buyPrice = d['third']['open'] + 0.5 * d['third']['barSize']
    stopPrice = d['second']['open']
    profitPrice = d['third']['close'] + d['third']['barSize']
    logging.info('found a potential buy point, buy:', buyPrice, ' stop:', stopPrice, ' profit:', profitPrice)
    if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
        logging.info('valid buy point, returning')
        return {'buyPrice': buyPrice, 'stopPrice': stopPrice, 'profitPrice': profitPrice }
    return None

def placeOrder(r):
    o = bracketOrder('BUY', 1, r['buyPrice'], r['profitPrice'], r['stopPrice'])
    t = ib.placeOrder(c, o)
    ib.sleep(1)
    logging.info('placed trade')
    return t


util.logToConsole(logging.INFO)
ib = IB()
ib.connect("localhost", 4002, clientId=2)

contract = Future('ES', '202006', 'GLOBEX')
#contract = Stock('TQQQ', 'SMART', 'USD', primaryExchange='NASDAQ')
ib.qualifyContracts(contract)
ticker = ib.reqMktData(contract, '', False, False)
ib.sleep(1)

data = {'first':None, 'second':None, 'third':None}
logging.info('getting first set of bars, ~180 seconds')
trade = None
for i in range(0, 10):
    if data['first'] is None and data['second'] is None:
        data['first'] = getNextBar(ticker, ib)
        data['second'] = getNextBar(ticker, ib)
    else:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = getNextBar(ticker, ib)
    logging.info(dumper.dump(data))
    result = analyze(data)
    if result is not None:
        trade = placeOrder(result)
        break
    else:
        logging.info('did not find a match to the pattern')


if trade is not None:
    while not trade.isDone():
        logging.info('waiting for fills:', trade.remaining())
        ib.sleep(1)

ib.cancelMktData(contract)
ib.disconnect()

sys.exit(0)
