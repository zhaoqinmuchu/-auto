# -*- coding: utf-8 -*-
"""诊断 SCL9 在 7/23 9:30-10:35 区间的合并K线、分型和笔"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, FX_TYPE

config = CChanConfig({
    "bi_strict": False,  # 新笔
    "macd_algo": "peak",
    "divergence_rate": float("inf"),
    "bsp2_follow_1": False,
    "bsp3_follow_1": False,
    "min_zs_cnt": 0,
    "bs_type": "1,1p,2,2s,3a,3b",
    "zs_algo": "normal",
    "cal_bi_zs": False,
    "cal_bi_bsp": False,
    "seg_algo": "chan",
})

chan = CChan(code="SCL9.txt", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=config)
chan.load()

kl_list = chan[0]

# 打印 9:30-10:35 的合并K线(CKLine)
print("--- 7/23 9:30-10:35 合并K线(CKLine) ---")
for klc in kl_list:
    t = klc.lst[0].time.to_str()
    if t.startswith("2026/07/23") and "09:3" <= t[11:] <= "10:35":
        fx = klc.fx
        fx_str = str(fx) if fx else "无"
        # 该合并K线包含的原始K线数
        n = len(klc.lst)
        print(f"合并K线{klc.idx}: {t} 高={klc.high:.1f} 低={klc.low:.1f} "
              f"({n}根原始K线) 分型={fx_str}")

print("\n--- 7/23 9:30-10:35 笔 ---")
for bi in kl_list.bi_list:
    b_t = bi.get_begin_klu().time.to_str()
    if b_t.startswith("2026/07/23") and "09:3" <= b_t[11:] <= "10:35":
        e_t = bi.get_end_klu().time.to_str()
        print(f"笔{bi.idx}: {b_t} -> {e_t}  {'UP' if bi.is_up() else 'DOWN'}  "
              f"begin={bi.get_begin_val():.1f} end={bi.get_end_val():.1f}")
