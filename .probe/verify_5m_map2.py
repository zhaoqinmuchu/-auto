# -*- coding: utf-8 -*-
"""验证"10秒数据 -> 5分钟映射导出"的定位口径（用用户导出的 AUL9 5分钟 TXT 作真值）。

方法：5 分钟K线的每个区间 [label-5min, label) 内理论上包含 30 根 10 秒K线，
其 10 秒标签 = label - k*10s (k=0..29)，日期字段沿用该 5 分钟K线的日期
（通达信用"交易日"标注夜盘）。把每个 10 秒标签交给导出用的映射函数，
结果必须正好等于该 5 分钟K线的 (日期, 时刻)。
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")
from datetime import datetime, timedelta
from DataAPI.TDX_TXT_API import TDX_TXT_API
from Common.CEnum import KL_TYPE, AUTYPE

PERIOD = 5
TXT = r"C:\Users\q8369\Desktop\AUL9.txt"


def period_label(t, period_min):
    sec = t.hour * 3600 + t.minute * 60 + (getattr(t, "second", 0) or 0)
    ps = period_min * 60
    lab = sec if sec % ps == 0 else ((sec // ps) + 1) * ps
    if lab >= 86400:
        lab -= 86400
    return lab // 3600, (lab % 3600) // 60


api = TDX_TXT_API(code=TXT, k_type=KL_TYPE.K_1M, begin_date="2026-10", end_date="2026-12", autype=AUTYPE.NONE)
bars = [(k.time, k) for k in api.get_kl_data()]
print("5M_BARS", len(bars), "first", bars[0][0].to_str(), "last", bars[-1][0].to_str())

check = 0
bad = []
for (t, k) in bars:
    base = datetime(t.year, t.month, t.day, t.hour, t.minute, getattr(t, "second", 0) or 0)
    for kk in range(30):
        src = base - timedelta(seconds=10 * kk)
        h, m = period_label(src, PERIOD)
        check += 1
        if (h, m) != (t.hour, t.minute):
            bad.append((src.strftime("%Y-%m-%d %H:%M:%S"), t.to_str(), h, m))
print("CHECKS", check, "MISMATCH", len(bad))
for x in bad[:10]:
    print("  BAD", x)

# 会话结构抽查：打印每天的分段（连续时间标签里出现的跳变）
print("---- 时间标签序列分段（节选） ----")
prev = None
segments = []
for (t, _) in bars:
    cur = (t.year, t.month, t.day, t.hour, t.minute)
    if prev is None:
        segments.append([cur, cur])
    else:
        # 间隔是否正好 5 分钟（跨日算断裂）
        dt_prev = datetime(*prev[:5])
        dt_cur = datetime(*cur[:5])
        gap = (dt_cur - dt_prev).total_seconds()
        if gap == 300:
            segments[-1][1] = cur
        else:
            segments.append([cur, cur])
    prev = cur
for s in segments[:16]:
    a, b = s
    print("  SEG %04d-%02d-%02d %02d:%02d -> %s %02d:%02d" % (
        a[0], a[1], a[2], a[3], a[4], ("%04d-%02d-%02d" % (b[0], b[1], b[2])) if b[:3] != a[:3] else "",
        b[3], b[4]))

# 边界标签抽样
keys = {(t.year, t.month, t.day, t.hour, t.minute) for (t, _) in bars}
for label in [(2026, 11, 6, 9, 5), (2026, 11, 6, 10, 15), (2026, 11, 6, 10, 35),
              (2026, 11, 6, 11, 30), (2026, 11, 6, 13, 35), (2026, 11, 6, 15, 0),
              (2026, 11, 6, 21, 5), (2026, 11, 6, 0, 0), (2026, 11, 6, 2, 30),
              (2026, 11, 9, 21, 5)]:
    print("HAS", label, label in keys)
