#!/usr/bin/python3
import sys
sys.path.append(r'.')
from api import config
from api import request

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('symbol', type=str, default=None)
args = parser.parse_args()

req = request.Request(config.Config())

print(req.quote(args.symbol))
