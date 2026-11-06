# -*- coding: utf-8 -*-
"""
验证跨年（2025-12 到 2026-02）倒推逻辑修复。

场景：通达信秒级K线无年份格式，数据跨 3 个月：
    2025-12: 30, 31
    2026-01: 1, 2, ..., 31
    2026-02: 1, 2, 3
用户填写最后一个K线所属年月为 2026-02。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataAPI.TDX_TXT_API import _infer_month_year_map


def build_days():
    """构造跨 3 个月的标注日序列（不去重，按时间顺序）。"""
    days = []
    days += [30, 31]                    # 2025-12
    days += list(range(1, 32))          # 2026-01 (1..31)
    days += [1, 2, 3]                   # 2026-02
    return days


def main():
    days = build_days()
    ref_date = (2026, 2)
    month_list = _infer_month_year_map(days, ref_date)

    assert len(month_list) == len(days), f"长度不匹配: {len(month_list)} != {len(days)}"

    # 期望结果
    expected = []
    expected += [(2025, 12)] * 2        # 30, 31 -> 2025-12
    expected += [(2026, 1)] * 31        # 1..31 -> 2026-01
    expected += [(2026, 2)] * 3         # 1,2,3 -> 2026-02

    ok = True
    for i, (d, (ym, exp)) in enumerate(zip(days, zip(month_list, expected))):
        if ym != exp:
            ok = False
            print(f"  错误: 索引{i} 标注日{d} -> {ym}, 期望 {exp}")

    if ok:
        print("[OK] 跨年倒推全部正确！")
        print("  2025-12: 30, 31")
        print("  2026-01: 1..31")
        print("  2026-02: 1, 2, 3")
    else:
        print("[FAIL] 存在错误！")
        sys.exit(1)

    # 额外验证：跨年边界（12月->1月）
    print("\n--- 额外验证：跨年边界 ---")
    days2 = [31, 1, 2]  # 12月31日, 1月1日, 1月2日
    ml2 = _infer_month_year_map(days2, (2026, 1))
    print(f"  [31,1,2] ref=(2026,1) -> {ml2}")
    assert ml2 == [(2025, 12), (2026, 1), (2026, 1)], f"跨年边界错误: {ml2}"
    print("[OK] 跨年边界正确")


if __name__ == "__main__":
    main()
