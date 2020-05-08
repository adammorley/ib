import asyncio
import logging
import socket
import yaml

from ib_insync import ibcontroller

class Config:
    account: str = None
    prod: bool = False
    tradingMode: str = None
    def __repr__(self):
        pieces = []
        for k, v in self.__dict__.items():
            pieces.append('{}:{}'.format(k, v))
        return ','.join(pieces)

def getConfig(configFile):
    config = Config()
    with open(configFile) as f:
        y = yaml.load(f)
        config.account = y['account']
        config.prod = y['prod']
        config.tradingMode = y['tradingMode']
    return config
    
def startGateway(configFile):
    conf = getConfig(configFile)
    logging.warn('config: {}'.format(conf))
    if conf.prod and conf.tradingMode != 'live':
        raise RuntimeError('prod is live')
    
    controller = ibcontroller.IBC(twsVersion=972, gateway=True, tradingMode=conf.tradingMode, ibcIni='/home/adam/ibcCreds/config.ini', ibcPath='/home/adam/ibc')
    logging.warn('starting API gateway in {} mode as user {}'.format(conf.tradingMode, user))
    controller.start()
    asyncio.get_event_loop().run_forever()
