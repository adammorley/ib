#!/usr/bin/python3

import collections
import dumper
import logging
from ib_insync import *

# pass in a ticker, will get the 60 second bars
# FIXME: split analysis of data from fetch
def collector(t, ib):
    d = { 'open': 0, 'close': 0, 'high': 0, 'low': 9223372036854775807, 'barSize': 0, 'lineSize': 0, 'color': 'X' }
    d['open'] = t.marketPrice()
    for i in range(0, 240):
        m = t.marketPrice()
        if m > d['high']:
            d['high'] = m
        elif m < d['low']:
            d['low'] = m
        ib.sleep(0.250)
    d['close'] = t.marketPrice()
    # FIXME: add unit test with high/low points outside bounds
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

#

util.logToConsole(logging.INFO)
ib = IB()
ib.connect("localhost", 4002, clientId=2)

contract = Future('ES', '202006', 'GLOBEX')
ib.qualifyContracts(contract)
ticker = ib.reqMktData(contract, '', False, False)
ib.sleep(1)

de = collections.deque()
for i in range(0, 6):
    d = collector(ticker, ib)
    de.append(d)

# run analysis function.  if it passes, place an order as needed
# if not, re-run collection process and re-analyze

ib.cancelMktData(contract)
ib.disconnect()
for i in de:
        dumper.dump(i)
        print("\n")
