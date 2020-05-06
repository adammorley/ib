import inspect
import logging

from ib_insync.contract import Contract
from ib_insync.contract import ContractDetails
from ib_insync.contract import Stock
from ib_insync.ib import IB
from ib_insync.objects import PriceIncrement

# wrapper for ib's contract since things are spread out among the contract and its details
class wContract:
    contract: Contract
    details: ContractDetails
    symbol: str
    localSymbol: str
    marketRule: [PriceIncrement]
    priceIncrement: float
    ibClient: IB
    def __init__(self, ibc, symbol, localSymbol=None):
        self.symbol = symbol
        self.localSymbol = localSymbol
        self.ibClient = ibc
        self.ibContract()
        self.qualify()
        self.ibDetails()
        self.marketRule()
        self.validatePriceIncrement()
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            if inspect.stack()[1].function == '__repr__' and k == 'details':
                continue # called from upper repr, be concise
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def ibContract(self):
        c = None
        if self.symbol == 'TQQQ' or self.symbol == 'AAPL' or self.symbol == 'AMZN' or self.symbol == 'FB' or self.symbol == 'GOOG':
            c = Stock(symbol=self.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
        elif self.symbol == 'SQQQ':
            c = Stock(symbol=self.symbol, exchange='SMART', currency='USD', primaryExchange='NASDAQ')
        elif self.symbol == 'AAP2' or self.symbol == 'AMZ2' or self.symbol == 'CRM2' or self.symbol == 'FB2' or self.symbol == 'GOO2' or self.symbol == 'GS2' or self.symbol == 'MSF2' or self.symbol == 'NFL2' or self.symbol == 'NVD2' or self.symbol == 'VIS2':
            c = Stock(symbol=self.symbol, exchange='SMART', currency='USD', primaryExchange='LSE')
        elif (self.symbol == 'ES' or self.symbol == 'NQ') and self.localSymbol != None:
            c = Contract(secType='FUT', symbol=self.symbol, localSymbol=self.localSymbol, exchange='GLOBEX', currency='USD')
        else:
            raise RuntimeError('no security specified')
        self.contract = c

    def qualify(self):
        r = self.ibClient.qualifyContracts(self.contract)
        if len(r) != 1 or r[0].symbol != self.symbol:
            raise LookupError('could not validate response: %s', r[0])
        if self.localSymbol == None: # sometimes the local symbol isn't passed in (like with stocks)
            if self.contract.localSymbol == None:
                raise LookupError('problem with looking up contract')
            else:
                self.localSymbol = self.contract.localSymbol

    def ibDetails(self):
        r = self.ibClient.reqContractDetails(self.contract)
        if len(r) != 1 or r[0].contract != self.contract:
            raise LookupError('problem getting contract details: %s', r)
        self.details = r[0]
        self.handleGlobexTimeZone()

    def handleGlobexTimeZone(self):
        if self.contract.exchange == 'GLOBEX' and self.details.timeZoneId == 'America/Belize': # CME/GLOBEX is in chicago not belize.
            self.details.timeZoneId = 'America/Chicago'

    def marketRule(self):
        if not isinstance(self.details.marketRuleIds, str):
            raise RuntimeError('wrong format {}'.format(self.details))
        mrStr = self.details.marketRuleIds
        mrs = mrStr.split(',')
        if len(mrs) < 1:
            raise RuntimeError('wrong format {}'.format(self.details))
        r0 = mrs[0]
        for r in mrs:
            if r != r0:
                raise RuntimeError('multiple market rules for a single contract {}'.format(self.details))
        mr = self.ibClient.reqMarketRule(r0)
        self.marketRule = mr
        penny = False
        if len(self.marketRule) > 1:
            for r in self.marketRule:
                if r.increment == 0.01:
                    penny = True
            if not penny:
                raise RuntimeError('multiple price incmrenets {} {}'.format(self.details, self.marketRule))
            logging.warn('default to a penny for the increment, multiple price increments found {} {}'.format(self.marketRule, self.symbol))
            self.priceIncrement = 0.01
        else:
            self.priceIncrement = self.marketRule[0].increment

    def validatePriceIncrement(self):
        if self.details.minTick != self.priceIncrement and len(self.marketRule) < 2:
            raise RuntimeError('ticks dont match: {} {}'.format(self.details.minTick, self.priceIncrement))
