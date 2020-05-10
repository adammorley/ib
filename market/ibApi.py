import asyncio
import atexit
import logging
import socket
import yaml

from ib_insync import ibcontroller
from ib_insync import IB

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

def getPort(prod=False):
    return 4001 if prod else 4002

def onConnected():
    logging.warn('watchdog ib client connected')
    
def startGatewayWatchdog(configFile):
    conf = getConfig(configFile)
    logging.warn('config: {}'.format(conf))
    if conf.prod and conf.tradingMode != 'live':
        raise RuntimeError('prod is live')
    
    controller = ibcontroller.IBC(twsVersion=972, gateway=True, tradingMode=conf.tradingMode, ibcIni='/home/adam/ibcCreds/config.ini', ibcPath='/home/adam/ibc')
    logging.warn('starting API gateway using watchdog in {} mode'.format(conf.tradingMode))
    ib = IB()
    ib.connectedEvent += onConnected
    watchdog = ibcontroller.Watchdog(controller=controller, ib=ib, host='localhost', port=getPort(conf.prod), appStartupTime=35)
    watchdog.start()

#    ib.sleep(30)
#    global pid
#    pid = watchdog.controller._proc.pid
#    def termChild():
#        import os
#        import signal
#        if pid is not None:
#            os.kill(pid, signal.SIGTERM)
#    atexit.register(termChild)

    ib.run()
