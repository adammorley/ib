#!/usr/bin/python3

import logging
import sys
import time

from ib_insync import *

sys.path.append(r'.')
from api import config
from api import request

from market import connect
from market import contract
from market import data

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--num', type=int, default=10)
args = parser.parse_args()

def r(f):
    return round(f, 2)

ibc = connect.connect(False)
util.logToConsole(logging.FATAL)
tqqq = contract.getContract('TQQQ', None)
ticker = data.getTicker(tqqq, ibc)

req = request.Request(config.Config())

for i in range(0, args.num):
    #ibc.sleep(1)
    #ibc.sleep(5)
    ibc.sleep(60)
    q = req.quote('TQQQ')
    s = []
    m = True
    if r(ticker.marketPrice()) != r(q.current):
        m = False
        s.append('cur; IB: {}, FH: {}'.format( r(ticker.marketPrice()), r(q.current) ))
    if r(ticker.high) != r(q.high):
        m = False
        s.append('high; IB: {}, FH: {}'.format( r(ticker.high), r(q.high) ))
    if r(ticker.low) != r(q.low):
        m = False
        s.append('low; IB: {}, FH: {}'.format( r(ticker.low), r(q.low) ))
    if r(ticker.open) != r(q.open):
        m = False
        s.append('open; IB: {}, FH: {}'.format( r(ticker.open), r(q.open) ))
    if r(ticker.close) != r(q.previousClose):
        m = False
        s.append('prevClose; IB: {}, FH: {}'.format( r(ticker.close), r(q.pc) ))
    if not m:
        s.append('bid/ask[IB]: {}, {}'.format( r(ticker.bid), r(ticker.ask) ))
        o = ''
        for i in range(0, len(s)):
            o += s[i]
            o += ', '
        o += 'IBt: {}, FHt: {}'.format( ticker.time.strftime('%Y-%m-%d %H:%M:%S'), time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(q.timestamp)) )
        print(o)
