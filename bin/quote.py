#!/usr/bin/python3
import sys
sys.path.append(r'.')
from api import config
from api import request

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-s','--symbol', action='append', type=str, default=None)
args = parser.parse_args()

req = request.Request(config.Config())

for s in args.symbol:
    print(req.quote(s))
