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
parser.add_argument('--conf', type=str, required=True)
parser.add_argument('--limitPrice', type=float, default=-1.0)
parser.add_argument('--bidIncrement', type=float, default=0.0)
parser.add_argument('--go', action='store_true', default=None)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

conf = config.getConfig(args.conf)
ibc = connect.connect(conf, args.debug)

wc = contract.wContract(ibc, conf.symbol, conf.localSymbol)

buyPrice = args.limitPrice
if buyPrice < 0: # fetch from market
    buyPrice = args.bidIncrement + wc.marketPrice()

from market.order import OrderDetails
orderDetails = OrderDetails(buyPrice, conf, wc)
logging.warn('created an order for contract %s %s', wc.contract, orderDetails)

orders = order.CreateBracketOrder(orderDetails, conf.account)

if args.go is not None:
    trades = trade.PlaceBracketTrade(orders, orderDetails, ibc)
    trade.CheckTradeExecution(trades, orderDetails)
else:
    logging.warn('would place this order: %s', orders)

connect.close(ibc)

sys.exit(0)
