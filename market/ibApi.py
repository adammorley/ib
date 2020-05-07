import asyncio
import logging
import socket
import yaml

from ib_insync import ibcontroller

def lookupUserPass():
    d = '/home/adam/.ibCreds/'
    u, p = d+'user', d+'pass'
    user, pass_ = None, None
    with open(u, 'r') as f:
        user = f.readline().replace('\n', '')
    with open(p, 'r') as f:
        pass_ = f.readline().replace('\n', '')
    return user, pass_

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
    
    user, password = lookupUserPass()
    controller = ibcontroller.IBC(twsVersion=972, gateway=True, tradingMode=conf.tradingMode, userid=user, password=password, ibcPath='/home/adam/ibc')
    logging.warn('starting API gateway in {} mode as user {}'.format(conf.tradingMode, user))
    controller.start()
    asyncio.get_event_loop().run_forever()
