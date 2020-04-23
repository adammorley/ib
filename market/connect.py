import logging
import sys

from ib_insync import *

from market import rand

def connect(logLevel):
    util.logToConsole(logLevel)
    ibc = IB()
    connected = False
    n = 0
    while not connected and n < 10:
        n += 1
        ibc.connect("localhost", 4002, clientId=rand.Int())
        ibc.sleep(1)
        connected = ibc.isConnected()
    if not ibc.isConnected():
        logging.fatal('did not connect.')
        sys.exit(1)
    return ibc
