import logging
import sys

from ib_insync import *

from market import rand

def getPort(prod=False):
    return 4001 if prod else 4002

def connect(debug=None, prod=False):
    util.logToConsole(logging.WARN)
    if debug:
        util.logToConsole(logging.DEBUG)

    ibc = IB()
    connected = False
    n = 0
    while not connected and n < 3:
        n += 1
        try:
            ibc.connect(host="localhost", port=getPort(prod), clientId=rand.Int())
            ibc.sleep(0.25)
            connected = ibc.isConnected()
        except:
            pass

    if not connected:
        raise RuntimeError('could not connect')
    return ibc

def close(ibc, c=None):
    if c is not None:
        ibc.cancelMktData(c)
        ibc.sleep(0)
    ibc.disconnect()
    ibc.sleep(0)
