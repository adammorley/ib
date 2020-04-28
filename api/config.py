import logging
import yaml

class Config:
    fhToken: str
    fhBaseUrl: str
    fhPriceTargetUrl: str
    fhQuoteUrl: str
    avApiKey: str
    avBaseUrl: str
    avDailyUrl: str

    def __init__(self, configFile='conf/api'):
        with open(configFile, 'r') as f:
            self.processConfig(yaml.load(f))
        
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

    def processConfig(self, conf):
        self.fhToken = conf['finnhub']['token']
        self.fhBaseUrl = conf['finnhub']['baseUrl']
        self.priceTargetUrl = self.fhBaseUrl + conf['finnhub']['priceTargetUrl'] + conf['finnhub']['key'] + self.fhToken + '&'
        self.quoteUrl = self.fhBaseUrl + conf['finnhub']['quoteUrl'] + conf['finnhub']['key'] + self.fhToken + '&'
        self.avApiKey = conf['alphav']['apiKey']
        self.baseUrl = conf['alphav']['baseUrl']
        self.dailyUrl = self.baseUrl + conf['alphav']['dailyUrl'] + conf['alphav']['key'] + self.avApiKey + '&'
        logging.debug('config: %s', self)
