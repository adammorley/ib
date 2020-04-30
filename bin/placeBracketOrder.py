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
parser.add_argument('--symbol', type=str, required=True)
parser.add_argument('--localSymbol', type=str, default=None)
parser.add_argument('--conf', type=str, required=True)
parser.add_argument('--limitPrice', type=float, default=-1.0)
parser.add_argument('--bidIncrement', type=float, default=0.0)
parser.add_argument('--go', action='store_true', default=None)
parser.add_argument('--prod', action='store_true', default=None)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

ibc = connect.connect(args.debug, args.prod)
conf = config.getConfig(args.conf)

wc = contract.wContract(ibc, args.symbol, args.localSymbol)

buyPrice = args.limitPrice
if buyPrice < 0: # fetch from market
    buyPrice = args.bidIncrement + data.getMarketPrice(data.getTick(wc, ibc))

from market.order import OrderDetails
orderDetails = OrderDetails(buyPrice, conf, wc)
logging.warn('created an order for contract %s %s', wc.contract, orderDetails)

orders = order.CreateBracketOrder(orderDetails)

if args.go is not None:
    trades = trade.PlaceBracketTrade(orders, orderDetails, ibc)
    trade.CheckTradeExecution(trades, orderDetails)
else:
    logging.warn('would place this order: %s', orders)

connect.close(ibc)

sys.exit(0)
