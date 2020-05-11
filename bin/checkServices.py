#!/usr/bin/python3
import logging
import os
import signal
import supervise
import sys
import time

services = '/home/adam/service/'
autoOrder_ES = services+'autoOrder_ES'
controller = services+'controller'
allServiceDirs = [autoOrder_ES, controller]

dirToService = {autoOrder_ES: supervise.Service(autoOrder_ES), controller: supervise.Service(controller)}
crashed = {autoOrder_ES: None, controller: None}
first = True

loopSleep=5

logging.basicConfig(level=logging.INFO)
logging.info('watching for crash loops and fatals...')
def term(*args):
    logging.warn('shutting down')
    sys.exit(0)
signal.signal(signal.SIGTERM, term)

while True:
    for d in allServiceDirs:
        if os.path.exists(d+'/'+'fatal'):
            logging.critical('saw a fatal error on {}'.format(t))

    if first:
        for d in allServiceDirs:
            uptime0 = dirToService[d].status().uptime
            time.sleep(loopSleep)
            uptime1 = dirToService[d].status().uptime
            if uptime0 > uptime1 or uptime0 < 2 and uptime1 < 2:
                crashed[d] = True
        first = False
    else:
        for d in allServiceDirs:
            uptime0 = dirToService[d].status().uptime
            time.sleep(loopSleep)
            uptime1 = dirToService[d].status().uptime
            if crashed[d] and (uptime0 > uptime1 or uptime0 < 2 and uptime1 < 2):
                logging.critical('serivce {} is crash looping'.format(d))
            else:
                crashed[d] = None
        first = True

    time.sleep(60)
