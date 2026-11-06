# -*- coding: utf-8 -*-
"""
端到端验证：构造跨 3 个月（2025-12 到 2026-02）的无年份格式 TXT 数据，
用 TDX_TXT_API 完整读取，确认 2025-12 的 K 线能被正确解析出来。
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataAPI.TDX_TXT_API import TDX_TXT_API
from Common.CEnum import KL_TYPE


def build_txt(path):
    """构造无年份格式(日/时:分:秒)的 TXT 数据，跨 3 个月。"""
    lines = []
    lines.append("时间\t开盘\t最高\t最低\t收盘\t成交量")
    # 2025-12: 30, 31
    for d in (30, 31):
        lines.append(f"{d}/10:00:00\t100\t110\t95\t105\t1000")
        lines.append(f"{d}/10:00:05\t105\t115\t100\t110\t1200")
    # 2026-01: 1..3
    for d in (1, 2, 3):
        lines.append(f"{d}/10:00:00\t110\t120\t105\t115\t1300")
        lines.append(f"{d}/10:00:05\t115\t125\t110\t120\t1400")
    # 2026-02: 1, 2
    for d in (1, 2):
        lines.append(f"{d}/10:00:00\t120\t130\t115\t125\t1500")
        lines.append(f"{d}/10:00:05\t125\t135\t120\t130\t1600")
    with open(path, 'w', encoding='gbk') as f:
        f.write("\n".join(lines) + "\n")


def main():
    tmp = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    tmp.close()
    build_txt(tmp.name)

    # 用户填写最后一个K线所属年月为 2026-02
    api = TDX_TXT_API(tmp.name, k_type=KL_TYPE.K_1M, begin_date="2026-02")
    kl_units = list(api.get_kl_data())

    # 统计各年月K线数量
    from collections import Counter
    cnt = Counter((k.time.year, k.time.month) for k in kl_units)

    print("各年月K线数量:", dict(sorted(cnt.items())))
    print("总K线数:", len(kl_units))

    # 期望：2025-12 有 4 根（30,31 各2根），2026-01 有 6 根，2026-02 有 4 根
    assert cnt.get((2025, 12)) == 4, f"2025-12 K线数错误: {cnt.get((2025, 12))}"
    assert cnt.get((2026, 1)) == 6, f"2026-01 K线数错误: {cnt.get((2026, 1))}"
    assert cnt.get((2026, 2)) == 4, f"2026-02 K线数错误: {cnt.get((2026, 2))}"

    # 验证时间顺序严格递增
    times = [(k.time.year, k.time.month, k.time.day, k.time.hour, k.time.minute, k.time.second) for k in kl_units]
    assert times == sorted(times), "K线时间顺序错误！"

    print("[OK] 端到端验证通过：2025-12 的 K 线能正确解析显示！")
    os.unlink(tmp.name)


if __name__ == "__main__":
    main()
