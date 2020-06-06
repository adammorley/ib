#!/usr/bin/python3

from datetime import datetime, timedelta
import pytz
import sys

sys.path.append(r'/home/adam/ib')
from market import connect
from market import config
from market import contract
from market import data

m = datetime.now().astimezone(pytz.timezone('America/New_York')).replace(minute=1, hour=10, microsecond=0, year=2020, month=4, day=25)
a = datetime.now().astimezone(pytz.timezone('America/New_York')).replace(minute=1, hour=15, microsecond=0, year=2020, month=4, day=25)

conf = config.getConfig('conf/FB')
ibc = connect.connect(conf)
fb = contract.wContract(ibc, 'FB', 'FB')
goog = contract.wContract(ibc, 'GOOG', 'GOOG')
amzn = contract.wContract(ibc, 'AMZN', 'AMZN')

fbD = 0.0
googD = 0.0
amznD = 0.0
for i in range(0, 90):
    for s in [fb, goog, amzn]:
        if m.weekday():
            mD = ibc.reqHistoricalData(contract=fb.contract, endDateTime=m.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            aD = ibc.reqHistoricalData(contract=fb.contract, endDateTime=a.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            fbD += aD[-1].close - mD[-1].close
            mD = ibc.reqHistoricalData(contract=goog.contract, endDateTime=m.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            aD = ibc.reqHistoricalData(contract=goog.contract, endDateTime=a.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            googD += aD[-1].close - mD[-1].close
            mD = ibc.reqHistoricalData(contract=amzn.contract, endDateTime=m.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            aD = ibc.reqHistoricalData(contract=amzn.contract, endDateTime=a.strftime('%Y%m%d %H:%M:%S EST'), durationStr='60 S', barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=2, keepUpToDate=False)
            amznD += aD[-1].close - mD[-1].close
    m += timedelta(days=1)
    a += timedelta(days=1)

print(fbD, googD, amznD)
