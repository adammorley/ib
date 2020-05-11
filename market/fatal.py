import logging
import pathlib
import sys

from market import config

fatalFilename = config.fatalFilename()

def serviceDir(conf):
    daemonName = sys.argv[0]
    return config.serviceDirs()+'/'daemonName+'_'conf.symbol

def touchDownFile(conf):
    pathlib.Path(serviceDir(conf)+'/'+config.downFilename()).touch()

def touchFatalFile(conf):
    pathlib.Path(serviceDir(conf)+'/'+config.fatalFilename()).touch()

def fatal(conf, msg):
    logging.critical(msg)
    touchFataFile(conf)
    touchDownFile(conf)
    sys.exit(1)

def errorAndExit(msg):
    logging.error(msg)
    sys.exit(1)
