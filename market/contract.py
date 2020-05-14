import inspect
import logging

from ib_insync.contract import Contract
from ib_insync.contract import ContractDetails
from ib_insync.contract import Stock
from ib_insync.ib import IB
from ib_insync.objects import PnLSingle
from ib_insync.objects import PriceIncrement
from ib_insync.objects import RealTimeBarList

from market import fatal

# wrapper for ib's contract since things are spread out among the contract and its details
class wContract:
    contract: Contract
    details: ContractDetails
    symbol: str
    localSymbol: str
    marketRule: [PriceIncrement]
    priceIncrement: float
    ibClient: IB
    pnl: PnLSingle
    bars: RealTimeBarList = None
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
            fatal.errorAndExit('no security specified')
        self.contract = c

    def qualify(self):
        r = self.ibClient.qualifyContracts(self.contract)
        if len(r) != 1 or r[0].symbol != self.symbol:
            fatal.errorAndExit('could not validate response: %s', r[0])
        if self.localSymbol == None: # sometimes the local symbol isn't passed in (like with stocks)
            if self.contract.localSymbol == None:
                fatal.errorAndExit('problem with looking up contract')
            else:
                self.localSymbol = self.contract.localSymbol

    # high/low/open are for the day
    def getTick(self):
        tick = self.ibClient.reqMktData(contract=self.contract, genericTickList='', snapshot=True, regulatorySnapshot=False)
        self.ibClient.sleep(1)
        return tick

    # high/low/open are for the day
    def getTicker(self):
        ticker = self.ibClient.reqMktData(contract=self.contract, genericTickList='', snapshot=False, regulatorySnapshot=False)
        self.ibClient.sleep(1)
        return ticker

    def ibDetails(self):
        r = self.ibClient.reqContractDetails(self.contract)
        if len(r) != 1 or r[0].contract != self.contract:
            fatal.errorAndExit('problem getting contract details: %s', r)
        self.details = r[0]
        self.handleGlobexTimeZone()

    def handleGlobexTimeZone(self):
        if self.contract.exchange == 'GLOBEX' and self.details.timeZoneId == 'America/Belize': # CME/GLOBEX is in chicago not belize.
            self.details.timeZoneId = 'America/Chicago'

    def marketPrice(self):
        tick = self.getTick()
        mp = tick.marketPrice()
        if math.isnan(mp):
            raise FloatingPointError('got floating point which is NaN: {} {}'.format(tick, self.symbol))
        return mp

    def marketRule(self):
        if not isinstance(self.details.marketRuleIds, str):
            fatal.errorAndExit('wrong format {}'.format(self.details))
        mrStr = self.details.marketRuleIds
        mrs = mrStr.split(',')
        if len(mrs) < 1:
            fatal.errorAndExit('wrong format {}'.format(self.details))
        r0 = mrs[0]
        for r in mrs:
            if r != r0:
                fatal.errorAndExit('multiple market rules for a single contract {}'.format(self.details))
        mr = self.ibClient.reqMarketRule(r0)
        self.marketRule = mr
        penny = False
        if len(self.marketRule) > 1:
            for r in self.marketRule:
                if r.increment == 0.01:
                    penny = True
            if not penny:
                fatal.errorAndExit('multiple price incmrenets {} {}'.format(self.details, self.marketRule))
            logging.warn('default to a penny for the increment, multiple price increments found {} {}'.format(self.marketRule, self.symbol))
            self.priceIncrement = 0.01
        else:
            self.priceIncrement = self.marketRule[0].increment

    def realtimeBars(self):
        if self.bars == None:
            self.bars = self.ibClient.reqRealTimeBars(self.contract, 5, 'MIDPOINT', False)
            self.bars.updateEvent += self.realtimeBarsUpdate
        else:
            logging.warn('already running realtime bars.')

    # keep just the last minute of bars
    def realtimeBarsUpdate(self, bb, new):
        if len(bb) > 12:
            for i in range(0, len(bb)-12):
                bb.pop(i)

    def realtimeHiLo(self):
        hi, lo = None, None
        for i in range(0, len(self.bars)):
                if hi == None or self.bars[i].high > hi:
                    hi = self.bars[i].high
                elif lo == None or self.bars[i].low < lo:
                    lo = self.bars[i].low
        return hi, lo

    def realtimeMidpoint(self):
        return self.bars[-1].close

    def updatePnl(self, account):
        pnlR = self.ibClient.pnlSingle(account=account, conId=self.contract.conId)
        if len(pnlR) != 1:
            fatal.errorAndExit('should get back one pnl for security: {} {}'.format(pnlR, self.contract))
        pnl = pnlR[0]
        if pnl.account != account:
            fatal.errorAndExit('got back mismatched accounts: {} {} {}'.format(pnl, account, self.contract))
        elif pnl.conId != self.contract.conId:
            fatal.errorAndExit('got back mismatched contract IDs: {} {} {}'.format(pnl, account, self.contract))
        self.pnl = pnl

    def validatePriceIncrement(self):
        if self.details.minTick != self.priceIncrement and len(self.marketRule) < 2:
            fatal.errorAndExit('ticks dont match: {} {}'.format(self.details.minTick, self.priceIncrement))
