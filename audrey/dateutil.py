import pytz
import datetime

def convert_aware_datetime(dt, tz_to):
    if type(tz_to) == str:
        tz_to = pytz.timezone(tz_to)
    return dt.astimezone(tz_to)

def convert_naive_datetime(dt, tz_from, tz_to):
    """
    Convert a naive datetime.datetime "dt" from one timezone to another.
    tz_from and tz_to may be either pytz.timezone instances, or timezone strings.
    Examples:
    Convert UTC datetime to US/Eastern:
    convert_datetime(datetime.datetime.utcnow(), pytz.utc, 'US/Eastern')

    Convert US/Eastern datetime to UTC:
    convert_datetime(datetime.datetime.now(), 'US/Eastern', pytz.utc)

    Convert US/Eastern datetime to ES/Pacific:
    convert_datetime(datetime.datetime.now(), 'US/Eastern', 'US/Pacific')
    """
    return convert_aware_datetime(make_aware(dt, tz_from), tz_to)

def make_naive(dt):
    return dt.replace(tzinfo=None)

def make_aware(dt, tz=pytz.utc):
    if type(tz) == str:
        tz = pytz.timezone(tz)
    return dt.replace(tzinfo=tz)

def utcnow(zero_seconds=False):
    """ Returns a timezone aware version of utcnow.
    (datetime.datetime.utcnow() returns a naive version.)
    If zero_seconds, the datetime will be rounded down to the minute.
    """
    now = datetime.datetime.now(pytz.utc)
    if zero_seconds: return now.replace(second=0, microsecond=0)
    return now
