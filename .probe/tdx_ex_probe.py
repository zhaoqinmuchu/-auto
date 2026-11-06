# -*- coding: utf-8 -*-
"""Probe TDX futures EX servers (from 期货通 connect.cfg [DSHOST]) via pytdx.

Read-only: connects, queries quotes/bars/ticks. No files written outside temp.
"""
import os
import sys
import time
import traceback

BASE = os.path.join(os.environ['TEMP'], 'pytdx_src', 'pytdx-1.72')
sys.path.insert(0, BASE)
from pytdx.exhq import TdxExHq_API  # noqa: E402

HOSTS = [('39.108.101.114', 7727), ('47.103.120.159', 7727)]


def trunc(o, n=300):
    s = repr(o)
    return s if len(s) <= n else s[:n] + '...'


def connect(ip, port):
    api = TdxExHq_API(heartbeat=False)
    try:
        ok = api.connect(ip, port, time_out=8)
    except TypeError:
        ok = api.connect(ip, port)
    print('CONNECT %s:%s -> %s' % (ip, port, ok))
    return api if ok else None


api = None
for ip, port in HOSTS:
    api = connect(ip, port)
    if api:
        print('USING HOST', ip)
        break
if not api:
    sys.exit('no host reachable')

print('api methods:', [m for m in dir(api) if m.startswith('get_')])


def call(label, fn, *a, **kw):
    try:
        r = fn(*a, **kw)
        n = len(r) if hasattr(r, '__len__') else '?'
        print('[%s] OK len=%s :: %s' % (label, n, trunc(r)))
        return r
    except Exception as e:
        print('[%s] ERR %s: %s' % (label, type(e).__name__, e))
        return None


print('=== basic ===')
call('instrument_count', api.get_instrument_count)
call('markets', api.get_markets)
call('quote(30,AUL9)', api.get_instrument_quote, 30, 'AUL9')
call('quote(30,AUL8)', api.get_instrument_quote, 30, 'AUL8')

print('=== bars categories ===')
for cat in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
    r = call('bars_cat%d' % cat, api.get_instrument_bars, cat, 30, 'AUL9', 0, 3)
    if r:
        print('    last:', trunc(r[-1], 320))
    time.sleep(0.05)

print('=== transactions (today) ===')
r = call('txn_today', api.get_transaction_data, 30, 'AUL9', 0, 5)
if r:
    print('    last:', trunc(r[-1], 320))

print('=== history transactions ===')
for d in (20261106, 20261103):
    r = call('hist_txn_%d' % d, api.get_history_transaction_data, 30, 'AUL9', d, 0, 5)
    if r:
        print('    last:', trunc(r[-1], 320))

print('=== history 1m bars range ===')
r = call('hist_bars_range', api.get_history_instrument_bars_range, 30, 'AUL9', 20261001, 20261106)
if r:
    print('    len', len(r), 'first:', trunc(r[0], 240), 'last:', trunc(r[-1], 240))

print('=== minute time data ===')
r = call('minute_today', api.get_minute_time_data, 30, 'AUL9')
if r:
    print('    len', len(r), 'first:', trunc(r[0], 200), 'last:', trunc(r[-1], 200))
r = call('minute_hist_20261106', api.get_history_minute_time_data, 30, 'AUL9', 20261106)
if r:
    print('    len', len(r), 'first:', trunc(r[0], 200), 'last:', trunc(r[-1], 200))

try:
    api.disconnect()
except Exception:
    pass
print('DONE')
