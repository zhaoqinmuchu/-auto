# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DataAPI.TDX_TXT_API import parse_tdx_time

f = open('SCL9.txt', 'r', encoding='gbk', errors='ignore')
lines = f.readlines()
out = []
prev = None
prevts = None
for i, l in enumerate(lines):
    l = l.strip()
    if not l or '-' not in l:
        continue
    t = l.split('\t')[0].strip()
    try:
        ct = parse_tdx_time(t)
    except Exception:
        continue
    if prevts is not None and ct.ts < prevts:
        out.append(f"乱序 line {i+1}: {prev} (ts={prevts}) -> {t} (ts={ct.ts})")
    prev = t
    prevts = ct.ts

# 统计日期范围
dates = set()
for l in lines:
    l = l.strip()
    if '-' in l:
        t = l.split('\t')[0].strip()
        if '/' in t:
            dates.add(t.split('-')[0])
out.append(f"日期范围: {min(dates)} ~ {max(dates)}")
out.append(f"总数据行数: {len([l for l in lines if '-' in l])}")

with open('_debug_out.txt', 'w', encoding='utf-8') as fo:
    fo.write('\n'.join(out) if out else 'NO ISSUES')
print("done")
