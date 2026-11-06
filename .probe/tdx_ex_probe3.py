# -*- coding: utf-8 -*-
"""Probe both 期货通 DSHOST hosts with pytdx, incl. category 12/13 (possible seconds K)."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.environ['TEMP'], 'pytdx_src', 'pytdx-1.72'))
from pytdx.exhq import TdxExHq_API  # noqa: E402

HOSTS = [('47.103.120.159', 7727), ('39.108.101.114', 7727)]


def trunc(o, n=300):
    s = repr(o)
    return s if len(s) <= n else s[:n] + '...'


for ip, port in HOSTS:
    print('######## %s:%d ########' % (ip, port))
    api = TdxExHq_API(heartbeat=False)
    try:
        ok = api.connect(ip, port, time_out=8)
    except TypeError:
        ok = api.connect(ip, port)
    print('connect ->', bool(ok))
    if not ok:
        continue
    for label, fn in (
        ('count', lambda: api.get_instrument_count()),
        ('info(0,3)', lambda: api.get_instrument_info(0, 3)),
        ('quote(30,AUL9)', lambda: api.get_instrument_quote(30, 'AUL9')),
        ('bars cat0', lambda: api.get_instrument_bars(0, 30, 'AUL9', 0, 3)),
        ('bars cat13', lambda: api.get_instrument_bars(13, 30, 'AUL9', 0, 3)),
        ('bars cat12', lambda: api.get_instrument_bars(12, 30, 'AUL9', 0, 3)),
        ('txn today', lambda: api.get_transaction_data(30, 'AUL9', 0, 3)),
        ('hist txn 20261106', lambda: api.get_history_transaction_data(30, 'AUL9', 20261106, 0, 3)),
        ('minute today', lambda: api.get_minute_time_data(30, 'AUL9')),
        ('hist bars range', lambda: api.get_history_instrument_bars_range(30, 'AUL9', 20261101, 20261106)),
    ):
        try:
            r = fn()
            n = len(r) if hasattr(r, '__len__') else '?'
            print('[%s] len=%s :: %s' % (label, n, trunc(r)))
        except Exception as e:  # noqa: BLE001
            print('[%s] ERR %s: %s' % (label, type(e).__name__, e))
        time.sleep(0.05)
    try:
        api.disconnect()
    except Exception:
        pass
print('DONE')
