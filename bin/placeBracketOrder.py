#!/usr/bin/python3

import datetime
import logging
import sys
import yaml
from os import path

from ib_insync import *

sys.path.append(r'.')

from market import bars
from market import config
from market import order
from market import rand
from market import trade

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', default=None)
parser.add_argument('--info', action='store_true', default=None)
parser.add_argument('--symbol', required=True)
parser.add_argument('--localSymbol')
parser.add_argument('--conf', required=True)
args = parser.parse_args()

def getConfig():
    if not path.isfile(args.conf):
        logging.fatal('need config file')
        sys.exit(1)
    with open(args.conf, 'r') as f:
        return config.ProcessConfig(yaml.load(f))

def getContract():
    if args.symbol == 'TQQQ':
        return Stock(symbol=args.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif args.symbol == 'SQQQ':
        return Stock(symbol=args.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif args.symbol == 'AAP2' or args.symbol == 'AMZ2' or args.symbol == 'CRM2' or args.symbol == 'FB2' or args.symbol == 'GOO2' or args.symbol == 'GS2' or args.symbol == 'MSF2' or args.symbol == 'NFL2' or args.symbol == 'NVD2':
        return Stock(symbol=args.symbol, exchange='SMART', currency='USD', primaryExchange='LSE')
    elif args.symbol == 'ES':
        return Contract(secType='FUT', symbol='ES', localSymbol=args.esLocal, exchange='GLOBEX', currency='USD')
    else:
        logging.fatal('no security specified')
        sys.exit(1)

util.logToConsole(logging.ERROR)
if args.info is not None:
    util.logToConsole(logging.INFO)
elif args.debug is not None:
    util.logToConsole(logging.DEBUG)
conf = getConfig()
logging.info('config %s', conf)
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

tick = ibc.reqMktData(contract=contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
ibc.sleep(1)

from market.order import Order
orderDetails = Order()
if tick.marketPrice() != tick.marketPrice():
    logging.fatal('NaN!')
    sys.exit(1)
logging.info('marketprice %f %s', tick.marketPrice(),tick.marketPrice())
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
