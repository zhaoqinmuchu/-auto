# -*- coding: utf-8 -*-
"""
测试通达信导出的"日线"TXT 数据（纯日期格式 YYYY/MM/DD，无时间部分）能否被正确读取。

背景：600570.txt 是日线数据，时间格式为 2017/12/29（只有日期，没有 -HH:MM 时间部分）。
修复前 _parse_tdx_time_str 无法解析这种格式，导致所有行被跳过，程序"无法打开"该文件。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataAPI.TDX_TXT_API import TDX_TXT_API, _parse_tdx_time_str, parse_tdx_time
from Common.CEnum import KL_TYPE

# 1) 单元测试：纯日期格式解析
print("=== 测试 _parse_tdx_time_str 纯日期格式 ===")
y, m, d, hh, mm, ss, is_daily = _parse_tdx_time_str("2017/12/29")
print(f"  2017/12/29 -> y={y} m={m} d={d} hh={hh} mm={mm} ss={ss} is_daily={is_daily}")
assert (y, m, d, hh, mm, ss, is_daily) == (2017, 12, 29, 0, 0, 0, True), "纯日期解析失败"

# 2) 单元测试：parse_tdx_time 对日线不做夜盘/隔夜日期调整
print("=== 测试 parse_tdx_time 日线（不调整日期） ===")
ct = parse_tdx_time("2017/12/29", is_futures=True)
print(f"  2017/12/29 -> {ct.year}/{ct.month}/{ct.day} {ct.hour}:{ct.minute}:{ct.second}")
assert (ct.year, ct.month, ct.day) == (2017, 12, 29), "日线日期被错误调整"
assert (ct.hour, ct.minute, ct.second) == (0, 0, 0), "日线时间应为 0:0:0"

# 3) 端到端测试：读取 600570.txt
print("=== 端到端测试：读取 600570.txt ===")
file_path = r"C:\Users\q8369\Desktop\600570.txt"
if not os.path.exists(file_path):
    print(f"  文件不存在: {file_path}")
    sys.exit(1)

api = TDX_TXT_API(code=file_path, k_type=KL_TYPE.K_DAY)
kl_units = list(api.get_kl_data())
print(f"  读取到 K 线数量: {len(kl_units)}")
assert len(kl_units) > 0, "未能读取到任何K线！"

print("  前5根K线:")
for klu in kl_units[:5]:
    t = klu.time
    print(f"    {t.year}/{t.month}/{t.day} {t.hour}:{t.minute}  open={klu.open} high={klu.high} low={klu.low} close={klu.close}")

print("  后3根K线:")
for klu in kl_units[-3:]:
    t = klu.time
    print(f"    {t.year}/{t.month}/{t.day} {t.hour}:{t.minute}  open={klu.open} high={klu.high} low={klu.low} close={klu.close}")

# 4) 验证时间严格递增（缠论框架要求）
print("=== 验证时间单调递增 ===")
prev_ts = None
monotonic = True
for klu in kl_units:
    if prev_ts is not None and klu.time.ts <= prev_ts:
        monotonic = False
        print(f"  时间戳不递增: {klu.time} ts={klu.time.ts} <= prev={prev_ts}")
        break
    prev_ts = klu.time.ts
print(f"  时间单调递增: {monotonic}")
assert monotonic, "K线时间戳未单调递增！"

# 5) 验证 is_daily_data() 自动判断
print("=== 测试 is_daily_data() 自动判断 ===")
daily_api = TDX_TXT_API(code=file_path)
print(f"  600570.txt is_daily_data = {daily_api.is_daily_data()}")
assert daily_api.is_daily_data() is True, "600570.txt 应被识别为日线数据"

# 用项目根目录的 SCL9.txt（分钟/秒级）验证非日线判断
scl9_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SCL9.txt")
if os.path.exists(scl9_path):
    scl9_api = TDX_TXT_API(code=scl9_path)
    print(f"  SCL9.txt is_daily_data = {scl9_api.is_daily_data()}")
    assert scl9_api.is_daily_data() is False, "SCL9.txt 不应被识别为日线数据"

# 6) 端到端：用 CChan 完整跑一遍缠论分析（日线级别）
print("=== 端到端：CChan 缠论分析（日线级别） ===")
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE
config = CChanConfig({"bi_strict": True, "trigger_step": False})
chan = CChan(
    code=file_path,
    data_src="custom:TDX_TXT_API.TDX_TXT_API",
    lv_list=[KL_TYPE.K_DAY],
    config=config,
    autype=AUTYPE.NONE,
)
print(f"  CChan 分析完成! K线数量: {len(chan[0])}")
assert len(chan[0]) > 0, "CChan 分析未产生K线！"

print("\n[OK] 600570.txt 日线数据读取成功！")
