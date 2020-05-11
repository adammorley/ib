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
restarted = {autoOrder_ES: None, controller: None}
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
            pid0 = dirToService[d].status().pid
            time.sleep(loopSleep)
            pid1 = dirToService[d].status().pid
            if pid0 != pid1:
                restarted[d] = True
        first = False
    else:
        for d in allServiceDirs:
            pid0 = dirToService[d].status().pid
            time.sleep(loopSleep)
            pid1 = dirToService[d].status().pid
            if restarted[d] and pid0 != pid1:
                logging.critical('serivce {} might be crash looping'.format(d))
            else:
                restarted[d] = None
        first = True

    time.sleep(60)
