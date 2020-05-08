import logging
import sys

from ib_insync import *

from market import rand

def getPort(prod=False):
    return 4001 if prod else 4002

def connect(conf=None, debug=None):
    util.logToConsole(logging.WARN)
    if debug:
        util.logToConsole(logging.DEBUG)

    ibc = IB()
    connected = False
    n = 0
    while not connected and n < 3:
        n += 1
        try:
            if conf.prod:
                if conf.tradingMode != 'live':
                    raise RuntimeError('prod set but trading mode is not live')
                ibc.connect(host="localhost", port=getPort(conf.prod), clientId=rand.Int(), timeout=3, readonly=False, account=conf.account)
            else:
                ibc.connect(host="localhost", port=getPort(conf.prod), clientId=rand.Int(), account=conf.account)
            ibc.sleep(0.25)
            connected = ibc.isConnected()
        except:
            pass

    if not connected:
        raise RuntimeError('could not connect')
    return ibc

def close(ibc, wc=None):
    if wc is not None:
        ibc.cancelMktData(wc.contract)
        ibc.sleep(0)
    ibc.disconnect()
    ibc.sleep(0)

def ping():
    ibc = IB()
    ibc.connect("localhost", port=getPort(False), clientId=rand.Int())
    ibc.disconnect()
    ibc.connect("localhost", port=getPort(True), clientId=rand.Int())
    ibc.disconnect()
