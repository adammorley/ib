#!/usr/bin/python3

import datetime
import logging
import sys
import yaml

from ib_insync import *

from market import bars
from market import order
from market import rand
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--symbol', required=True)
args = parser.parse_args()

def getContract():
    if args.symbol == 'TQQQ':
        return Stock(symbol=args.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif args.symbol == 'SQQQ':
        return Stock(symbol=args.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif args.symbol == 'ES00':
        return Contract(secType='FUT', symbol='ES', localSymbol=args.esLocal, exchange='GLOBEX', currency='USD')
    else:
        logging.fatal('no security specified')
        sys.exit(1)

with open('conf/qqq', 'r') as f:
    conf = yaml.load(f)

startTime = datetime.datetime.utcnow()

util.logToConsole(logging.DEBUG)
ibc = IB()
ibc.connect("localhost", 4002, clientId=rand.Int())
ibc.sleep(1)
if not ibc.isConnected():
    logging.fatal('did not connect.')
    sys.exit(1)

logging.info('connected, qualifying contract')
contract = getContract()
qc = ibc.qualifyContracts(contract)
if len(qc) != 1 or qc[0].symbol != args.symbol:
    logging.fatal('could not validate contract: %s', qc)
    sys.exit(1)

ticker = ibc.reqMktData(contract, '', False, False)
ibc.sleep(1)

logging.info('running trade loop')
data = {'first':None, 'second':None, 'third':None}
while datetime.datetime.utcnow() < startTime + datetime.timedelta(hours=24):
    if data['first'] is None and data['second'] is None:
        data['first'] = bars.GetNextBar(ticker, ibc.sleep)
        data['second'] = bars.GetNextBar(ticker, ibc.sleep)
    else:
        data['first'] = data['second']
        data['second'] = data['third']
    data['third'] = bars.GetNextBar(ticker, ibc.sleep)
    orderDetails = order.Analyze(data, conf)
    if orderDetails is not None:
        positions = ibc.positions()
        ibc.sleep(0)
        makeTrade = True
        for p in positions:
            if p.contract == contract and p.position >= conf.qty * conf.openPositions:
                logging.info('passing on trade as max positions already open')
                logging.info(orderDetails)
                makeTrade = False
        if makeTrade:
            orders = order.CreateBracketOrder(contract, orderDetails, conf)
            trades = trade.PlaceBracketTrade(contract, orders, ibc)
            logging.debug(trades)
            logging.info(ibc.positions())
    else:
        logging.info('did not find a trade')

ibc.cancelMktData(contract)
ibc.sleep(1)
ibc.disconnect()

sys.exit(0)
