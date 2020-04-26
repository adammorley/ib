import logging
import sys

from ib_insync import *

from market import rand

def connect(logLevel):
    util.logToConsole(logLevel)
    ibc = IB()
    connected = False
    n = 0
    while not connected and n < 3:
        n += 1
        try:
            ibc.connect("localhost", 4002, clientId=rand.Int())
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
