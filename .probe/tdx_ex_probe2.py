# -*- coding: utf-8 -*-
"""Probe TDX futures EX + MAC-EX servers (期货通 connect.cfg DSHOST) via eltdx.

Read-only. Focus: is there a seconds-level K line / tick history for AUL9?
"""
import os
import sys
import traceback
from dataclasses import fields, is_dataclass

sys.path.insert(0, os.path.join(os.environ['TEMP'], 'eltdx_whl'))
from eltdx.ex import ExTdxClient, MacExClient  # noqa: E402
from eltdx.mac import Period  # noqa: E402

HOST = '39.108.101.114'
PORT = 7727


def show(label, obj, n=4):
    try:
        if obj is None:
            print('[%s] None' % label)
            return
        if isinstance(obj, (list, tuple)):
            print('[%s] len=%d' % (label, len(obj)))
            for x in obj[:n]:
                print('    ', repr(x)[:460])
        else:
            print('[%s] %s' % (label, repr(obj)[:460]))
    except Exception as e:  # noqa: BLE001
        print('[%s] show-err %s' % (label, e))


def fieldnames(obj):
    try:
        if is_dataclass(obj):
            return [f.name for f in fields(type(obj))]
    except Exception:
        pass
    return None


print('############ EX protocol ############')
c = ExTdxClient(host=HOST, port=PORT, timeout=10.0, auto_failover=False, probe_on_connect=False)
try:
    c.connect()
    print('EX connected', getattr(c, 'host', '?'))
    try:
        print('count =', c.get_instrument_count())
    except Exception as e:
        print('count ERR', type(e).__name__, e)
    for label, fn in (
        ('markets', lambda: c.get_markets()),
        ('info0', lambda: c.get_instrument_info(0, 3)),
        ('quote 30 AUL9', lambda: c.get_instrument_quote(30, 'AUL9')),
        ('quote 30 AUL8', lambda: c.get_instrument_quote(30, 'AUL8')),
    ):
        try:
            show(label, fn())
        except Exception as e:
            print('[%s] ERR %s: %s' % (label, type(e).__name__, e))

    for cat in (0, 4, 7, 8, 13):
        try:
            r = c.get_instrument_bars(cat, 30, 'AUL9', 0, 5)
            show('bars cat=%d' % cat, r, 5)
            if r:
                print('     fields:', fieldnames(r[0]))
        except Exception as e:
            print('[bars cat=%d] ERR %s: %s' % (cat, type(e).__name__, e))

    try:
        r = c.get_history_instrument_bars_range(30, 'AUL9', 20261020, 20261106)
        if r:
            print('[hist_bars_range] len=%d fields=%s' % (len(r), fieldnames(r[0])))
            print('     first:', repr(r[0])[:300])
            print('     last :', repr(r[-1])[:300])
        else:
            print('[hist_bars_range] None/empty')
    except Exception as e:
        print('[hist_bars_range] ERR %s: %s' % (type(e).__name__, e))

    for label, fn in (
        ('txn today', lambda: c.get_transaction_data(30, 'AUL9', 0, 5)),
        ('hist txn 20261106', lambda: c.get_history_transaction_data(30, 'AUL9', 20261106, 0, 5)),
        ('minute today', lambda: c.get_minute_time_data(30, 'AUL9')),
        ('minute hist 20261106', lambda: c.get_history_minute_time_data(30, 'AUL9', 20261106)),
    ):
        try:
            r = fn()
            show(label, r, 5)
            if r:
                print('     fields:', fieldnames(r[0]))
        except Exception as e:
            print('[%s] ERR %s: %s' % (label, type(e).__name__, e))
finally:
    try:
        c.close()
    except Exception:
        pass

print('############ MAC-EX protocol ############')
try:
    m = MacExClient(host=HOST, port=PORT, timeout=10.0)
    m.connect()
    print('MACEX connected')
    for label, fn in (
        ('quotes', lambda: m.goods_quotes([(30, 'AUL9')])),
        ('kline SECONDS', lambda: m.goods_kline(30, 'AUL9', Period.SECONDS, 0, 8)),
        ('kline MIN_1', lambda: m.goods_kline(30, 'AUL9', Period.MIN_1, 0, 5)),
        ('kline MIN_5', lambda: m.goods_kline(30, 'AUL9', Period.MIN_5, 0, 5)),
        ('txn today', lambda: m.goods_transaction(30, 'AUL9', None, 0, 5)),
        ('tick_chart', lambda: m.goods_tick_chart(30, 'AUL9')),
    ):
        try:
            r = fn()
            show(label, r, 8)
            if isinstance(r, list) and r:
                print('     fields:', fieldnames(r[0]))
        except Exception as e:
            print('[%s] ERR %s: %s' % (label, type(e).__name__, e))
    try:
        import datetime
        r = m.goods_transaction(30, 'AUL9', datetime.date(2026, 11, 6), 0, 5)
        show('txn 2026-11-06', r, 5)
    except Exception as e:
        print('[txn hist] ERR %s: %s' % (type(e).__name__, e))
    try:
        m.close()
    except Exception:
        pass
except Exception:
    traceback.print_exc()

print('DONE')
