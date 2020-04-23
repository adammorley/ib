#!/usr/bin/python3

import datetime
import logging
import sys
import yaml

from ib_insync import *

sys.path.append(r'.')

from market import bars
from market import config
from market import connect
from market import contract
from market import order
from market import rand
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--symbol', required=True)
args = parser.parse_args()

startTime = datetime.datetime.utcnow()
ibc = connect.connect(logging.INFO)
util.logToConsole(logging.INFO)
conf = config.getConfig('conf/QQQ')
logging.info('config %s', conf)

logging.info('connected, qualifying contract')
contract = contract.getContract(args.symbol, None)
qc = ibc.qualifyContracts(contract)
if len(qc) != 1 or qc[0].symbol != args.symbol:
    logging.fatal('could not validate contract: %s', qc)
    sys.exit(1)

ticker = ibc.reqMktData(contract=contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
ibc.sleep(1)

logging.info('running trade loop...')
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
                makeTrade = False
        if makeTrade:
            orders = order.CreateBracketOrder(contract, orderDetails)
            trades = trade.PlaceBracketTrade(contract, orders, ibc)
            logging.debug(trades)
            logging.info('placed a trade')

ibc.cancelMktData(contract)
ibc.sleep(1)
ibc.disconnect()

sys.exit(0)
