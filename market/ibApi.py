import asyncio
import logging
import socket
import yaml

from ib_insync import ibcontroller
from ib_insync import IB

sys.path.append(r'/home/adam/svc')
from svc import paths

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
    
# note that the watchdog and signal handling here requires a pause between signals
def startGatewayWatchdog(configFile):
    conf = getConfig(configFile)
    logging.warn('config: {}'.format(conf))
    if conf.prod and conf.tradingMode != 'live':
        raise RuntimeError('prod is live')

    controller = ibcontroller.IBC(twsVersion=972, gateway=True, tradingMode=conf.tradingMode, ibcIni=paths.creds()+'/config.ini', ibcPath=paths.rootDir()+'/ibc')
    logging.warn('starting API gateway using watchdog in {} mode'.format(conf.tradingMode))
    ib = IB()
    ib.connectedEvent += onConnected
    watchdog = ibcontroller.Watchdog(controller=controller, ib=ib, host='localhost', port=getPort(conf.prod), appStartupTime=35)
    watchdog.start()

    import signal
    import sys
    import time
    def term(*args):
        logging.warn('shutting down controller')
        watchdog.controller._proc.send_signal(signal.SIGTERM)
        time.sleep(1)
        logging.warn('shutting down watchdog')
        sys.exit(0)
    signal.signal(signal.SIGTERM, term)

    ib.run()
