# -*- coding: utf-8 -*-
"""查看各 TXT 的时间标签约定（夜盘跨零点、收盘/开盘标签），判断映射口径。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")
from DataAPI.TDX_TXT_API import TDX_TXT_API
from Common.CEnum import KL_TYPE, AUTYPE

files = {
    "AUL9_5m": (r"C:\Users\q8369\Desktop\AUL9.txt", "2026-10"),
    "SCL9_1m": (r"C:\Users\q8369\Desktop\SCL9.txt", "2026-06"),
}
for name, (path, begin) in files.items():
    api = TDX_TXT_API(code=path, k_type=KL_TYPE.K_1M, begin_date=begin, end_date="2026-12", autype=AUTYPE.NONE)
    klus = list(api.get_kl_data())
    print("=" * 30, name, "bars=", len(klus))
    if not klus:
        continue
    print("first:", klus[0].time.to_str(), "last:", klus[-1].time.to_str())
    # 每个日期的时间范围
    from collections import OrderedDict
    days = OrderedDict()
    for k in klus:
        t = k.time
        d = (t.year, t.month, t.day)
        hhmm = t.hour * 100 + t.minute
        if d not in days:
            days[d] = [hhmm, hhmm, 1]
        else:
            days[d][0] = min(days[d][0], hhmm)
            days[d][1] = max(days[d][1], hhmm)
            days[d][2] += 1
    for d, (a, b, n) in days.items():
        print("  date %04d-%02d-%02d  n=%3d  first=%04d  last=%04d" % (d[0], d[1], d[2], n, a, b))
    # 打印跨午夜前后各 4 根
    idx = [i for i, k in enumerate(klus) if k.time.hour == 0 and k.time.minute <= 10]
    for i in idx[:6]:
        print("  --- around 00:00 ---")
        for j in range(max(0, i - 3), min(len(klus), i + 4)):
            t = klus[j].time
            print("     %s  o=%.2f h=%.2f l=%.2f c=%.2f" % (t.to_str(), klus[j].open, klus[j].high, klus[j].low, klus[j].close))
