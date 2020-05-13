import logging
import pathlib
import sys
import time

sys.path.append(r'/home/adam/svc')
from svc import paths

def serviceDir(conf):
    daemonName = sys.argv[0]
    return paths.serviceDirs() + conf.localSymbol

def touchDownFile(conf):
    pathlib.Path(serviceDir(conf) + paths.downFilename()).touch()

def touchFatalFile(conf):
    pathlib.Path(serviceDir(conf) + paths.fatalFilename()).touch()

def fatal(conf, msg):
    logging.critical(msg)
    touchFatalFile(conf)
    touchDownFile(conf)
    sys.exit(1)

def errorAndExit(msg):
    logging.error(msg)
    time.sleep(5)
    sys.exit(1)
