from ib_insync.contract import Contract
from ib_insync.contract import ContractDetails
from ib_insync.contract import Stock

class iContract:
    contract: Contract
    details: ContractDetails
    symbol: str
    localSymbol: str


def getContract(symbol, localSymbol=None):
    if symbol == 'TQQQ':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif symbol == 'SQQQ':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
    elif symbol == 'AAP2' or symbol == 'AMZ2' or symbol == 'CRM2' or symbol == 'FB2' or symbol == 'GOO2' or symbol == 'GS2' or symbol == 'MSF2' or symbol == 'NFL2' or symbol == 'NVD2' or symbol == 'VIS2':
        return Stock(symbol=symbol, exchange='SMART', currency='USD', primaryExchange='LSE')
    elif (symbol == 'ES' or symbol == 'NQ') and localSymbol != None:
        return Contract(secType='FUT', symbol=symbol, localSymbol=localSymbol, exchange='GLOBEX', currency='USD')
    raise RuntimeError('no security specified')

def valid(c, r):
    if len(r) != 1 or r[0].symbol != c.symbol or r[0].localSymbol != contract.localSymbol:
        raise LookupError('could not validate response: %s', r)

def qualify(contract, ibc):
    valid(ibc.qualifyContracts(contract))

def details(contract, ibc):
    cd = ibc.reqContractDetails(contract):
    valid(cd)
    return cd
