#!/usr/bin/python3

import datetime
import dumper
import logging
import sys

from ib_insync import *

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--profitPrice', type=float, required=True)
parser.add_argument('--security', required=True)
parser.add_argument('--stopPrice', type=float, required=True)
parser.add_argument('--qty', type=int, required=True)
parser.add_argument('--ops', type=int, required=True) # number of open positions to maintain
parser.add_argument('--trail', action='store_true', required=False)
args = parser.parse_args()

import random
import string

def getContract():
    if args.security == 'TQQQ':
        return Stock('TQQQ', 'SMART', 'USD', primaryExchange='NASDAQ')
    elif args.security == 'ES00':
        return Future('ES', '202006', 'GLOBEX')
    else:
        logging.fatal('no contract specified')
        sys.exit(1)

def randomString(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

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
    bar.close = bar.open
    bar.low = bar.open
    bar.high = bar.open
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
    profitPrice: float = 0.0
    stopPrice: float = 0.0

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
    if not d['third'].barSize > d['second'].barSize:
        return None

    #buyPrice = d['third'].open + 0.5 * d['third'].barSize
    #buyPrice = bar.open + bar.barSize * 0.5 # simulating buying at market in next interval
    if args.trail:
        stopPrice = args.stopPrice
    else:
        stopPrice = d['second'].close - args.stopPrice
    buyPrice = d['third'].close
    profitPrice = d['third'].close + args.profitPrice
    logging.info('found a potential buy point, buy: %d, stop: %d, profit: %d', buyPrice, stopPrice, profitPrice)

    #if profitPrice - buyPrice > buyPrice - stopPrice: # bigger on win side, more momo
    if True:
        logging.debug('valid buy point, returning')
        od = OrderDetails()
        od.stopPrice = stopPrice
        od.buyPrice = buyPrice
        od.profitPrice = profitPrice
        return od
    return None

# the back testing assumes the trade is placed in the next 1 minute window or canceled.
def placeOrder(c, od):
    bo = Order(orderId=ib.client.getReqId(), transmit=False, action='BUY', totalQuantity=qty, orderType='LMT', lmtPrice=od.buyPrice, tif='DAY', outsideRth=True)
    po = Order(orderId=ib.client.getReqId(), parentId=bo.orderId, action='SELL', totalQuantity=qty, orderType='LMT', lmtPrice=od.profitPrice, tif='GTC', outsideRth=True)
    if args.trail:
        so = Order(orderId=ib.client.getReqId(), parentId=bo.orderId, action='SELL', totalQuantity=qty, orderType='TRAIL', auxPrice=od.stopPrice, tif='GTC', outsideRth=True)
    else:
        so = Order(orderId=ib.client.getReqId(), parentId=bo.orderId, action='SELL', totalQuantity=qty, orderType='STP', auxPrice=od.stopPrice, tif='GTC', outsideRth=True)
    oca = ib.oneCancelsAll([po, so], ocaType=1, ocaGroup=randomString())
    t = dict()
    for o in [bo, po, so]:
        t[o] = ib.placeOrder(c, o)
    ib.sleep(0)
    n = 0
    while n < 10 and t[bo].orderStatus.status != 'Filled':
        n += 1
        ib.sleep(1)
    logging.info('placed orders')
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
contract = getContract()
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
    orderDetails = analyze(data)
    if orderDetails is not None:
        positions = ib.positions()
        ib.sleep(0)
        for p in positions:
            if p.contract == contract and p.position >= args.qty * args.ops:
                logging.info('passing on trade as max positions already open')
                logging.info(orderDetails)
            else:
                trades = placeOrder(contract, orderDetails)
                logging.debug(trades)
    else:
        logging.info('did not find a trade')
    logging.info(ib.positions())
    logging.info(ib.openOrders())

ib.cancelMktData(contract)
ib.sleep(1)
ib.disconnect()

sys.exit(0)
