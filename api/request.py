from json import JSONDecodeError
import requests

from api.config import Config
class Request:
    config: Config
    def __init__(self, c):
        self.config = c

    def daily(self, s):
        return self.makeRequest( self.config.dailyUrl + self.symbol(s) )

    def makeRequest(self, url):
        r = requests.get(url)
        assert r.status_code == 200, 'got non-200'
        try:
            return r.json()
        except JSONDecodeError:
            return None

    def priceTarget(self, s):
        return self.makeRequest( self.config.priceTargetUrl + self.symbol(s) )

    def quote(self, s):
        return self.makeRequest( self.config.quoteUrl + self.symbol(s) )

    def symbol(self, s):
        return 'symbol=' + s


