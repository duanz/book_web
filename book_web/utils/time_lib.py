# -*- coding: utf-8 -*-

import re
import time
import math
import pytz
import datetime

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7
CN_TIMESTAMP_INTERVAL = 8 * HOUR
CN_TZ = pytz.timezone('Asia/Shanghai')

def timestamp_to_utc_str(timestamp, _format='%Y-%m-%d %H:%M:%S', timezone=0):
    """根据时区将将时间戳转换为时间(string)"""
    if not isinstance(timestamp, int) or timestamp < 0:
        return timestamp
    _timestamp = timestamp + 3600 * timezone
    _datetime = datetime.datetime.utcfromtimestamp(_timestamp)
    return _datetime.strftime(_format)


def timestamp_to_cst_str(timestamp, _format='%Y-%m-%d %H:%M:%S'):
    """将时间戳转换成北京时间(string)"""
    return timestamp_to_utc_str(timestamp, _format=_format, timezone=8)


class UTC(datetime.tzinfo):
    """UTC 时区, 用法
        UTC('+8:00')为UTC时间 +8小时, 即北京时间时区
        UTC('-5:00')为UTC时间 -5小时

        默认获取当前datetime为"系统本地时间":
        datetime.datetime.now() => localtime(即本地时间)
        指定获取北京时间:
        datetime.datetime.now(tz=UTC('+8:00')) => 北京时间(+8区)
        建议通过使用此模块下的now方法获取"北京时间"的datetime, 即:
        time_lib.now()
    """
    def __init__(self, utc):
        utc = str(utc.strip().upper())
        re_utc = re.compile(r'^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')
        mt = re_utc.match(utc)
        if mt:
            minus = mt.group(1) == '-'
            hours = int(mt.group(2))
            minutes = int(mt.group(3))
            if minus:
                hours, minutes = -hours, -minutes
            self._tzname = 'UTC{}'.format(utc)
            self._utcoffset = datetime.timedelta(
                hours=hours, minutes=minutes)
        else:
            raise ValueError('invalid utc time zone')

    def utcoffset(self, dt):
        return self._utcoffset

    def tzname(self, dt):
        return self._tzname

    def dst(self, dt):
        return datetime.timedelta(0)

    def __str__(self):
        return 'UTC tzinfo object ({})'.format(self._tzname)

    __repr__ = __str__

TZ_CST = UTC('+8:00')


def now(tz=TZ_CST):
    """根据时区获取当前datetime, 默认北京时间"""
    return datetime.datetime.now(tz=tz)


def now_str(_format='%Y-%m-%d %H:%M:%S', tz=TZ_CST):
    """today()的字符串格式"""
    return now(tz=tz).strftime(_format)


def today(tz=TZ_CST):
    """根据时区获取date, 默认北京时间"""
    return now(tz=tz).date()


def tomorrow():
    return today() + datetime.timedelta(days=1)


def yesterday():
    return today() - datetime.timedelta(days=1)


def today_str(_format='%Y-%m-%d', tz=TZ_CST):
    """today()的字符串格式"""
    return now(tz=tz).date().strftime(_format)


def str_to_datetime(_datetime, _format):
    """datetime字符串转datetime"""
    return datetime.datetime.strptime(_datetime, _format)


def date_str_to_date(date, _format, to_utc=True, end_of_day=False):
    """日期字符串转date"""
    _datetime = str_to_datetime(date, _format)
    if end_of_day:
        _time = datetime.datetime(_datetime.year, _datetime.month, _datetime.day, 23, 59, 59)
    else:
        _time = datetime.datetime(_datetime.year, _datetime.month, _datetime.day)
    if to_utc:
        _time = CN_TZ.localize(_time)
        return _time.astimezone(pytz.utc)
    return _time


def cn_date_str_to_date(date, end_of_day=False):
    """中国日期字符串转date"""
    return date_str_to_date(date, _format='%Y年%m月%d日', end_of_day=end_of_day)


def add_date_interval(date, inter):
    """获取与date间隔inter天的date"""
    assert isinstance(date, datetime.date)
    return date + datetime.timedelta(days=inter)


def add_today_interval(inter):
    """获取与今天间隔inter天的date"""
    return add_date_interval(today(), inter)


def _add_month_interval(dt, inter):
    # 求n月后的自然年, 月
    m = dt.month + inter - 1
    y = dt.year + m // 12
    m = m % 12 + 1
    return (y, m)


def add_month_interval(dt, inter):
    # 求dt经过inter自然月后的日期, dt是datetime, inter是int
    y, m = _add_month_interval(dt, inter)
    # dt所在月的最大日
    y2, m2 = _add_month_interval(dt, inter + 1)
    maxD = (datetime.date(y2, m2, 1) - datetime.timedelta(days=1)).day
    # 超出最大日期选最大日期, 反之为dt所在日
    d = dt.day if dt.day <= maxD else maxD
    return datetime.date(y, m, d)


def month_differ(x, y):
    # 求x, y两个月份的自然月差
    month_differ = abs((x.year - y.year) * 12 + (x.month - y.month))
    return month_differ


def last_date_of_month(date):
    """求传入的date(`datetime`或`date`类型)所在月份的最后一天"""
    year, month = _add_month_interval(date, 1)
    last_date = datetime.date(year, month, 1) - datetime.timedelta(days=1)
    return last_date


def is_last_date_of_this_month():
    """判断今天是否是本月最后一天"""
    _today = today()
    return _today == last_date_of_month(_today)


def timestamp():
    return int(time.time())


def get_timestamp_by_interval_days(interval, is_cn=True):
    """获取与当前时间间隔interval天的时间戳"""
    assert isinstance(interval, int)
    return get_timestamp_by_date(add_today_interval(interval), is_cn=is_cn)


def get_timestamp_by_date(date, is_cn=True):
    """获取日期date的时间戳(即当天00:00的时间戳)"""
    assert isinstance(date, (datetime.date, datetime.datetime))
    # mktime使用的是localtime, 取的是localtime对应的timestamp, 需要加上和utc的偏差值
    _timestamp = int(time.mktime(date.timetuple()))
    offset_hour = get_offset_hour_between_sys_n_utc()
    utc_timestamp = _timestamp + offset_hour * HOUR
    if is_cn:
        return utc_timestamp - CN_TIMESTAMP_INTERVAL
    return utc_timestamp


def get_today_timestamp_range_tuple():
    """获取今天的时间戳范围"""
    _min = get_timestamp_by_date(today())
    _max = get_timestamp_by_date(tomorrow())
    return (_min, _max)


def get_week_timestamp_range_tuple():
    """获取7天内的时间戳范围"""
    _max = get_timestamp_by_date(tomorrow())
    _min = get_timestamp_by_date(today() - datetime.timedelta(days=7))
    return (_min, _max)


def get_month_timestamp_range_tuple():
    """获取30天内的时间戳范围"""
    _max = get_timestamp_by_date(tomorrow())
    _min = get_timestamp_by_date(today() - datetime.timedelta(days=30))
    return (_min, _max)


def cn_date_str_to_int(date, combine=True):
    r = re.match(r'(\d{4})年(\d{2})月(\d{2})日', date)
    return int(''.join(r.groups())) if combine else [int(i) for i in r]


def compare_date_input(start_date, end_date, allow_equal=False):
    start = cn_date_str_to_int(start_date)
    end = cn_date_str_to_int(end_date)
    return (start <= end) if allow_equal else (start < end)


def today_int():
    return int(today_str('%Y%m%d'))


def get_offset_hour_between_sys_n_utc():
    """获取系统时间与UTC时间的小时差"""
    utcnow = datetime.datetime.utcnow()
    sysnow = datetime.datetime.now()

    # 获取UTC和local的绝对时间差(秒数)
    delta = sysnow - utcnow
    delta_seconds = delta.seconds

    if delta.days < 0:
        delta_seconds = -(24 * HOUR - delta_seconds)

    is_negative = delta_seconds < 0
    abs_delta_seconds = abs(delta_seconds)

    # 忽略一分钟以内的偏差
    if abs_delta_seconds < (1 * MINUTE):
        return 0

    # 向上取整(会忽略小于一个时区的偏差)
    abs_offset_hour = int(math.ceil(abs_delta_seconds / HOUR))
    return -abs_offset_hour if is_negative else abs_offset_hour


def get_offset_hour_between_sys_n_cst():
    """获取系统时间与北京时间的小时差"""
    return get_offset_hour_between_sys_n_utc() - 8


def get_sys_hour_by_cst_hour(cst_hour):
    """获取北京时间的`小时`对应的系统时间的`小时`"""
    if not isinstance(cst_hour, int) and cst_hour not in range(0, 24):
        raise ValueError('cst_hour must be int and between 0~23')
    run_hour = cst_hour + get_offset_hour_between_sys_n_cst()
    if run_hour < 0:
        run_hour += 24
    return run_hour


def get_timestamp_by_cn_date_str(cn_date_str, _format='%Y年%m月%d日'):
    _date = date_str_to_date(cn_date_str, _format=_format)
    return get_timestamp_by_date(_date, is_cn=True)


def date_to_int(date, fmt='%Y%m%d'):
    return int(date.strftime(fmt))


def get_first_date_of_next_month_by_date(date):
    _next = add_month_interval(date, 1)
    return datetime.date(year=_next.year, month=_next.month, day=1)


def get_last_date_of_month_by_date(date):
    return get_first_date_of_next_month_by_date(date) - datetime.timedelta(days=1)


def get_month_timestamp_range_by_date(date):
    first = datetime.date(year=date.year, month=date.month, day=1)
    last = get_first_date_of_next_month_by_date(date)
    ts_first = get_timestamp_by_date(first)
    ts_last = get_timestamp_by_date(last)
    return ts_first, ts_last


def get_now_time_stamp():
    """获取当前时间戳，如：20180820160605220"""
    ct = time.time()
    local_time = time.localtime(ct)
    data_head = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    data_secs = (ct - int(ct)) * 1000
    time_stamp = "%s.%03d" % (data_head, data_secs)
    stamp = ("".join(time_stamp.split()[0].split("-"))+"".join(time_stamp.split()[1].split(":"))).replace('.', '')
    return stamp
