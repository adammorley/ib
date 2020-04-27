from datetime import datetime, timedelta
import pytz
import re

from datetimerange import DateTimeRange # https://pypi.org/project/DateTimeRange/

def parseOpenHours(cd):
    return parseTradingHours(cd.tradingHours, parseTimezone(cd.timeZoneId) )

# parse the timezoneId
def parseTimezone(timeZoneId):
    assert isinstance(timeZoneId, str), 'timeZoneId should be a string'
    for tz in pytz.all_timezones:
        if tz == timeZoneId:
            return pytz.timezone(tz)
    assert False, 'timeZoneId must be a valid timezone'

# parse the contract details into datetime objects
def parseTradingHours(tradingHours, tz):
    assert isinstance(tradingHours, str), 'trading hours is a string'
    openHours = []
    # '20200427:0930-20200427:1600;20200428:0930-20200428:1600'
    ranges = tradingHours.split(';')
    m = re.compile('.*:CLOSED')
    for range_ in ranges:
        if m.match(range_): # skip closed days
            continue
        ts = range_.split('-')
        #assert len(ts) == 2, 'only two timestamps per range'
        start = datetime.strptime(ts[0], '%Y%m%d:%H%M')
        end = datetime.strptime(ts[1], '%Y%m%d:%H%M')
        r = DateTimeRange(start.replace(tzinfo=tz), end.replace(tzinfo=tz))
        assert r.is_valid_timerange()
        openHours.append(r)
    return openHours

def createIntersectedRange(r0, r1):
    r = r0.intersection(r1)
    if r.is_valid_timerange():
        return r
    return None

def createIntersectedRanges(r0, r1):
    intersect = []
    for r0_ in r0:
        for r1_ in r1:
            r = createIntersectedRange(r0_, r1_)
            if r is not None:
                intersect.append(r)
    return intersect

def getNextOpenTime(r):
    d = datetime.utcnow()
    d = d + timedelta(hours=1)
    d = d.replace(minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
    for r_ in r:
        t = d
        n = 0
        while t not in r_ and n < 384: # ~8 days
            n += 1
            t = t + timedelta(minutes=30)
        if t in r_:
            return t
    return None
