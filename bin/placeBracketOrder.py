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
parser.add_argument('--symbol', required=True)
parser.add_argument('--localSymbol')
parser.add_argument('--conf', required=True)
args = parser.parse_args()

logLevel = logging.INFO
if args.debug:
    logLevel = logging.DEBUG
ibc = connect.connect(logLevel)
conf = config.getConfig(args.conf)
logging.info('config %s', conf)
logging.info('connected, qualifying contract')
contract = contract.getContract(args.symbol, args.localSymbol)
qc = ibc.qualifyContracts(contract)
if len(qc) != 1 or qc[0].symbol != args.symbol:
    logging.fatal('could not validate contract: %s', qc)
    sys.exit(1)

tick = ibc.reqMktData(contract=contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
ibc.sleep(1)

from market.order import Order
orderDetails = Order()
if tick.marketPrice() != tick.marketPrice():
    logging.fatal('NaN!')
    sys.exit(1)
orderDetails.buyPrice = tick.marketPrice() + 0.50
orderDetails.config = conf
logging.info('created an order for contract %s %s', contract, orderDetails)

orders = order.CreateBracketOrder(contract, orderDetails)
logging.info('created bracket orders %s', orders)

trades = trade.PlaceBracketTrade(contract, orders, ibc)
logging.info('trades in flight %s', trades)

ibc.cancelMktData(contract)
ibc.sleep(1)
ibc.disconnect()

sys.exit(0)
