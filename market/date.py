from datetime import datetime, timedelta
import logging
import pytz
import re

from datetimerange import DateTimeRange # https://pypi.org/project/DateTimeRange/

from market import fatal

def nowInUtc():
    return datetime.utcnow().astimezone(pytz.utc)

def highVolumeHours(cd):
    return parseLiquidHours(cd.liquidHours, parseTimezone(cd.timezone) )

# returns datetimerange of open hours for next month or so
def openHours(cd):
    return parseTradingHours(cd.tradingHours, parseTimezone(cd.timeZoneId) )

# parse the timezoneId
def parseTimezone(timeZoneId):
    if not isinstance(timeZoneId, str):
        fatal.errorAndExit('timeZoneId should be a string')
    return pytz.timezone(timeZoneId)

def parseIbHours(ibHours, tz):
    if not isinstance(ibHours, str):
        fatal.errorAndExit('trading hours is a string')
    openHours = []
    # '20200427:0930-20200427:1600;20200428:0930-20200428:1600'
    ranges = ibHours.split(';')
    m = re.compile('.*:CLOSED')
    for range_ in ranges:
        if range_ == '':
            continue
        if m.match(range_): # skip closed days
            continue
        ts = range_.split('-')
        if len(ts) != 2:
            fatal.errorAndExit('only two timestamps per range: {}     {}'.format(ts, ibHours))
        start = tz.localize(datetime.strptime(ts[0], '%Y%m%d:%H%M')).astimezone(pytz.utc)
        end = tz.localize(datetime.strptime(ts[1], '%Y%m%d:%H%M')).astimezone(pytz.utc)
        r = DateTimeRange(start, end)
        if not r.is_valid_timerange():
            fatal.errorAndExit('should get a valid timerange')
        openHours.append(r)
    logging.debug('openHours: %s', openHours)
    return openHours

def parseLiquidHours(liquidHours, tz):
    return parseIbHours(liquidHours, tz)

# parse the contract details into datetime objects
def parseTradingHours(tradingHours, tz):
    return parseIbHours(tradingHours, tz)

def createIntersectedRange(r0, r1):
    r = r0.intersection(r1)
    if r.is_valid_timerange():
        return r
    return None

# can be used to intersect the NYSE and LSE for example
def createIntersectedRanges(r0, r1):
    intersect = []
    for r0_ in r0:
        for r1_ in r1:
            r = createIntersectedRange(r0_, r1_)
            if r is not None:
                intersect.append(r)
    return intersect

def getNextOpenTime(r):
    dt = nowInUtc()
    dt = dt + timedelta(hours=1)
    dt = dt.replace(minute=0, second=0, microsecond=0)
    for r_ in r:
        n = 0
        while dt not in r_ and n < 384: # ~8 days
            n += 1
            dt = dt + timedelta(minutes=30)
        if dt in r_:
            return dt
    return None

def isMarketOpen(cd, dt=None):
    return _isMarketOpen(openHours(cd), dt)

def _isMarketOpen(r, dt):
    if dt is None:
        dt = nowInUtc()
    for r_ in r:
        if dt in r_:
            return True
    return False

def marketOpenedLessThan(cd, td=None):
    return _marketOpenedLessThan(openHours(cd), td)

def _marketOpenedLessThan(r, td):
    dt = nowInUtc()
    if len(r) < 2:
        fatal.errorAndExit('seems like this might not be a range')
    for r_ in r:
        if dt not in r_:
            continue
        elif dt - td not in r_:
            return True
    return False

def marketNextCloseTime(cd):
    return _marketNextCloseTime(openHours(cd))

def _marketNextCloseTime(r):
    dt = nowInUtc()
    if len(r) < 2:
        fatal.errorAndExit('seem like this might not be a range')
    for r_ in r:
        if dt in r_:
            return r_.end_datetime
    fatal.errorAndExit('cannot find next close time {} {}'.format(dt, r))

def marketOpenedAt(cd):
    return _marketOpenedAt(openHours(cd))

def _marketOpenedAt(r):
    dt = nowInUtc()
    if len(r) < 2:
        fatal.errorAndExit('seem like this might not be a range')
    for r_ in r:
        if dt in r_:
            return r_.start_datetime
    fatal.errorAndExit('cannot find market open time {} {}'.format(dt, r))

def ibMaintWindow():
    est = pytz.timezone('America/New_York')
    start = est.localize(datetime.now().replace(hour=23, minute=45, second=0, microsecond=0)).astimezone(pytz.utc)
    end = est.localize((datetime.now() + timedelta(days=1)).replace(hour=0, minute=45, second=0, microsecond=0)).astimezone(pytz.utc)
    return DateTimeRange(start, end)

def inIbMaintWindow():
    return nowInUtc() in ibMaintWindow()
