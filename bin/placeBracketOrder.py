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
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--symbol', type=str, required=True)
parser.add_argument('--localSymbol', type=str)
parser.add_argument('--conf', type=str, required=True)
parser.add_argument('--limitPrice', type=float, default=0.0)
parser.add_argument('--bidIncrement', type=float, default=0.0)
parser.add_argument('--go', action='store_true', default=None)
args = parser.parse_args()

def setBuyPrice(contract, ibc):
    if args.limitPrice:
        return args.limitPrice
    tick = ibc.reqMktData(contract=contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
    ibc.sleep(1)
    if tick.marketPrice() != tick.marketPrice:
        logging.fatal('NaN!')
        sys.exit(1)
    bp = tick.marketPrice() + args.bidIncrement
    ibc.cancelMktData(contract)
    ib.sleep(0)
    return bp

logLevel = logging.INFO
if args.debug:
    logLevel = logging.DEBUG
ibc = connect.connect(logLevel)
conf = config.getConfig(args.conf)
logging.info('config %s', conf)
contract = contract.getContract(args.symbol, args.localSymbol)
qc = ibc.qualifyContracts(contract)
if len(qc) != 1 or qc[0].symbol != args.symbol:
    logging.fatal('could not validate contract: %s', qc)
    sys.exit(1)

from market.order import OrderDetails
orderDetails = OrderDetails()
orderDetails.config = conf
orderDetails.buyPrice = setBuyPrice(contract, ibc)

logging.info('created an order for contract %s %s', contract, orderDetails)

orders = order.CreateBracketOrder(contract, orderDetails)
logging.info('created bracket orders %s', orders)

if args.go:
    trades = trade.PlaceBracketTrade(contract, orders, ibc)
    logging.info('trades in flight %s', trades)
else:
    logging.info('would place this order: %s', orders)

ibc.disconnect()

sys.exit(0)
