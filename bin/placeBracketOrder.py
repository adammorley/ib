#!/usr/bin/python3

import logging
import sys

sys.path.append(r'.')
from market import bars
from market import config
from market import connect
from market import contract
from market import data
from market import order
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--symbol', type=str, required=True)
parser.add_argument('--localSymbol', type=str)
parser.add_argument('--conf', type=str, required=True)
parser.add_argument('--limitPrice', type=float, default=-1.0)
parser.add_argument('--bidIncrement', type=float, default=0.0)
parser.add_argument('--go', action='store_true', default=None)
args = parser.parse_args()

logLevel = logging.WARN
if args.debug:
    logLevel = logging.DEBUG

ibc = connect.connect(logLevel)
conf = config.getConfig(args.conf)

c = contract.getContract(args.symbol, args.localSymbol)
contract.qualify(c, ibc)

buyPrice = args.limitPrice
if buyPrice < 0: # fetch from market
    buyPrice = args.bidIncrement + data.getMarketPrice(data.getTick(c, ibc))

from market.order import OrderDetails
orderDetails = OrderDetails(buyPrice, conf, c)
logging.warn('created an order for contract %s %s', c, orderDetails)

orders = order.CreateBracketOrder(orderDetails)

if args.go is not None:
    trades = trade.PlaceBracketTrade(orders, orderDetails, ibc)
    trade.CheckTradeExecution(trades)
else:
    logging.warn('would place this order: %s', orders)

connect.close(ibc)

sys.exit(0)
