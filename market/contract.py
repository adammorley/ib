import logging
import sys

from ib_insync.contract import Contract
from ib_insync.contract import Stock

def getContract(symbol, localSymbol):
    if symbol == 'TQQQ':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif symbol == 'SQQQ':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif symbol == 'AAP2' or symbol == 'AMZ2' or symbol == 'CRM2' or symbol == 'FB2' or symbol == 'GOO2' or symbol == 'GS2' or symbol == 'MSF2' or symbol == 'NFL2' or symbol == 'NVD2':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='LSE')
    elif symbol == 'ES':
        return Contract(secType='FUT', symbol=symbol, localSymbol=localSymbol, exchange='GLOBEX', currency='USD')
    else:
        logging.fatal('no security specified')
        sys.exit(1)

