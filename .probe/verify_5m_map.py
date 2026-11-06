# -*- coding: utf-8 -*-
"""验证 10 秒数据 -> 5 分钟映射导出：
1) 把 AUL9 10 秒 K 线按"结束时刻"聚合成 5 分钟 K 线；
2) 与用户给出的通达信 5 分钟 TXT 样例（硬编码若干行）对照 OHLC；
3) 用与 GUI 相同的映射公式生成端点定位条件，检查打到的 5 分钟K线存在；
4) 打印若干条映射后的 DRAWLINE 语句样例。
只读，不修改任何文件。
"""
import sys
sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, AUTYPE

TXT = r"C:\Users\q8369\Desktop\AUL9.txt"
conf = CChanConfig({
    "trigger_step": False, "print_warning": False,
    "bi_strict": False, "bi_fx_check": "loss", "bi_end_is_peak": False,
})
chan = CChan(code=TXT, begin_time="2026-11", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=conf, autype=AUTYPE.NONE)
kl = chan[0]
klus = []
for klc in kl.lst:
    klus.extend(klc.lst)
klus.sort(key=lambda k: k.idx)
print("KLU_CNT", len(klus), "FIRST", klus[0].time.to_str(), "LAST", klus[-1].time.to_str())

PERIOD = 5


def period_label(t, period_min):
    sec = t.hour * 3600 + t.minute * 60 + (getattr(t, "second", 0) or 0)
    ps = period_min * 60
    lab = sec if sec % ps == 0 else ((sec // ps) + 1) * ps
    if lab >= 86400:
        lab -= 86400
    return lab // 3600, (lab % 3600) // 60


def cond(t, period_min):
    date_val = 1000000 + (t.year % 100) * 10000 + t.month * 100 + t.day
    h, m = period_label(t, period_min)
    if h == 0 and m == 0:
        return f"DATE={date_val} AND TIME=0"
    return f"DATE={date_val} AND TIME={h * 100 + m}"


# 聚合到 5 分钟
bars = {}
for k in klus:
    t = k.time
    h, m = period_label(t, PERIOD)
    key = (t.year, t.month, t.day, h, m)
    if key not in bars:
        bars[key] = [k.open, k.high, k.low, k.close, float(k.volume), 1]
    else:
        b = bars[key]
        b[1] = max(b[1], k.high)
        b[2] = min(b[2], k.low)
        b[3] = k.close
        b[4] += float(k.volume)
        b[5] += 1
print("BARS_5M", len(bars))

# 样例（来自用户 m01064 贴出的通达信 5 分钟导出）：日期,时,分,开,高,低,收,量
samples = [
    (2026, 11, 6, 9, 5, 882.82, 882.82, 879.70, 880.66, 9595),
    (2026, 11, 6, 9, 10, 880.66, 882.00, 880.24, 880.38, 5153),
    (2026, 11, 6, 10, 15, 876.48, 877.60, 875.88, 876.76, 4223),
    (2026, 11, 6, 10, 35, 876.94, 877.42, 875.34, 875.96, 3503),
    (2026, 11, 6, 13, 35, 871.22, 871.38, 869.64, 871.10, 6802),
    (2026, 11, 6, 15, 0, 872.20, 872.46, 872.04, 872.04, 2630),
    (2026, 11, 6, 0, 45, 886.34, 886.66, 886.10, 886.48, 1716),
    (2026, 11, 9, 21, 5, 876.54, 876.60, 874.28, 874.44, 5861),
    (2026, 11, 9, 21, 10, 874.44, 875.16, 874.40, 874.54, 2806),
    (2026, 11, 9, 21, 15, 874.52, 874.76, 874.10, 874.26, 2358),
]
ok = 0
for (y, mo, d, hh, mm, o, hi, lo, cl, vol) in samples:
    k = (y, mo, d, hh, mm)
    if k not in bars:
        print("MISSING", k)
        continue
    b = bars[k]
    good = (abs(b[0] - o) < 0.005 and abs(b[1] - hi) < 0.005
            and abs(b[2] - lo) < 0.005 and abs(b[3] - cl) < 0.005)
    ok += 1 if good else 0
    print("SAMPLE", k, "OK" if good else "DIFF",
          "agg=(%.2f,%.2f,%.2f,%.2f,vol=%.0f,n=%d)" % (b[0], b[1], b[2], b[3], b[4], b[5]),
          "sample=(%.2f,%.2f,%.2f,%.2f,vol=%d)" % (o, hi, lo, cl, vol))
print("SAMPLE_MATCH", ok, "/", len(samples))

# 线段端点映射检查
segs = kl.seg_list
miss = []
for i, seg in enumerate(segs):
    for which in ("begin", "end"):
        klu = getattr(seg.start_bi, "get_begin_klu")() if which == "begin" else getattr(seg.end_bi, "get_end_klu")()
        t = klu.time
        h, m = period_label(t, PERIOD)
        key = (t.year, t.month, t.day, h, m)
        if key not in bars:
            miss.append((i, which, t.to_str(), cond(t, PERIOD)))
print("SEG_CNT", len(segs), "ENDPOINT_MISS", len(miss))
for x in miss[:10]:
    print("  MISS_ENDPOINT", x)

# 打印几条映射后的 DRAWLINE 样例
print("---- DRAWLINE 样例 ----")
for i, seg in enumerate(segs[:5]):
    bk = seg.start_bi.get_begin_klu()
    ek = seg.end_bi.get_end_klu()
    print("DRAWLINE(%s, %.2f, %s, %.2f, 0),COLORYELLOW,LINETHICK1;" % (
        cond(bk.time, PERIOD), seg.start_bi.get_begin_val(),
        cond(ek.time, PERIOD), seg.end_bi.get_end_val()))

# 00:00 / 23:5x 边界单测（用日期时间模拟）
from datetime import datetime
for dt in (datetime(2026, 11, 9, 0, 0, 0), datetime(2026, 11, 6, 23, 59, 50),
           datetime(2026, 11, 6, 9, 3, 0), datetime(2026, 11, 6, 9, 5, 0)):
    print("EDGE", dt.strftime("%Y-%m-%d %H:%M:%S"), "->", cond(dt, PERIOD))
