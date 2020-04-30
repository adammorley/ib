from json import JSONDecodeError
import requests

from api.config import Config
from api.quote import Quote
class Request:
    config: Config
    def __init__(self, c):
        self.config = c

    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def daily(self, s):
        return self.makeRequest( self.config.dailyUrl + self.symbol(s) )

    def makeRequest(self, url):
        r = requests.get(url)
        if r.status_code != 200:
            raise RuntimeError('got a non-200')
        try:
            return r.json()
        except JSONDecodeError:
            return None

    def priceTarget(self, s):
        return self.makeRequest( self.config.priceTargetUrl + self.symbol(s) )

    def quote(self, s):
        q = self.makeRequest( self.config.quoteUrl + self.symbol(s) )
        return Quote(s, q['c'], q['h'], q['l'], q['o'], q['pc'], q['t'])

    def symbol(self, s):
        return 'symbol=' + s


