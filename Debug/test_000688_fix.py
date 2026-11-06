# -*- coding: utf-8 -*-
"""验证 000688.txt 中 OHLC 不合法脏数据在 autofix=True 下被正确修正"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataAPI.TDX_TXT_API import TDX_TXT_API
from Common.CEnum import KL_TYPE

file_path = r"C:\Users\q8369\Desktop\000688.txt"
print(f"数据文件: {file_path}")

api = TDX_TXT_API(code=file_path, k_type=KL_TYPE.K_1M)
count = 0
target = None
for klu in api.get_kl_data():
    count += 1
    # 找到 2026/01/15 15:00 那根K线
    t = klu.time
    if (t.year, t.month, t.day, t.hour, t.minute) == (2026, 1, 15, 15, 0):
        target = klu

print(f"K线总数: {count}")
if target is not None:
    print("2026/01/15 15:00 修正后:")
    print(f"  open={target.open} high={target.high} low={target.low} close={target.close}")
    assert target.high >= max(target.low, target.open, target.high, target.close) - 1e-9, "high 仍不是最大值!"
    assert target.low <= min(target.low, target.open, target.high, target.close) + 1e-9, "low 仍不是最小值!"
    print("  [OK] high/low 已修正为合法值")
else:
    print("未找到 2026/01/15 15:00 的K线")

print("导入成功，未抛出 OHLC 校验异常")
