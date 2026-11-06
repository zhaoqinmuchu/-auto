# -*- coding: utf-8 -*-
"""
验证用户真实场景：有年份格式(YYYY/MM/DD-HH:MM)数据跨 2025-11 到 2026-01，
用户填写参考年月 2026-02 时，2025 的数据不应被误删。

修复前：begin_date="2026-02" 被当作字符串过滤截止，
"2025/11/14-10:35" < "2026-02" 为 True，导致 2025 全部被过滤掉。
修复后：begin_date 为年月(YYYY-MM)时仅作参考基准，不做过滤。
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataAPI.TDX_TXT_API import TDX_TXT_API
from Common.CEnum import KL_TYPE


def build_txt(path):
    """构造有年份格式(YYYY/MM/DD-HH:MM)的 TXT 数据，跨 2025-11 到 2026-01。"""
    lines = []
    lines.append("时间\t开盘\t最高\t最低\t收盘\t成交量")
    # 2025-11: 14, 15
    for d in (14, 15):
        lines.append(f"2025/11/{d}-10:35\t100\t110\t95\t105\t1000")
        lines.append(f"2025/11/{d}-10:40\t105\t115\t100\t110\t1200")
    # 2025-12: 30, 31
    for d in (30, 31):
        lines.append(f"2025/12/{d}-10:35\t110\t120\t105\t115\t1300")
        lines.append(f"2025/12/{d}-10:40\t115\t125\t110\t120\t1400")
    # 2026-01: 15, 16
    for d in (15, 16):
        lines.append(f"2026/01/{d}-10:35\t120\t130\t115\t125\t1500")
        lines.append(f"2026/01/{d}-10:40\t125\t135\t120\t130\t1600")
    with open(path, 'w', encoding='gbk') as f:
        f.write("\n".join(lines) + "\n")


def main():
    tmp = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    tmp.close()
    build_txt(tmp.name)

    # 用户填写参考年月 2026-02（有年份格式数据，年月仅作参考，不应过滤）
    api = TDX_TXT_API(tmp.name, k_type=KL_TYPE.K_1M, begin_date="2026-02")
    kl_units = list(api.get_kl_data())

    from collections import Counter
    cnt = Counter((k.time.year, k.time.month) for k in kl_units)

    print("各年月K线数量:", dict(sorted(cnt.items())))
    print("总K线数:", len(kl_units))

    # 期望：2025-11 有 4 根，2025-12 有 4 根，2026-01 有 4 根（共 12 根）
    assert cnt.get((2025, 11)) == 4, f"2025-11 K线数错误: {cnt.get((2025, 11))}"
    assert cnt.get((2025, 12)) == 4, f"2025-12 K线数错误: {cnt.get((2025, 12))}"
    assert cnt.get((2026, 1)) == 4, f"2026-01 K线数错误: {cnt.get((2026, 1))}"
    assert len(kl_units) == 12, f"总K线数错误: {len(kl_units)}"

    # 验证时间顺序严格递增
    times = [(k.time.year, k.time.month, k.time.day, k.time.hour, k.time.minute, k.time.second) for k in kl_units]
    assert times == sorted(times), "K线时间顺序错误！"

    print("[OK] 有年份格式数据：填写参考年月 2026-02 时，2025 数据能正确显示！")
    os.unlink(tmp.name)


if __name__ == "__main__":
    main()
