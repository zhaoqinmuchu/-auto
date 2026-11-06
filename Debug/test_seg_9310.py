# -*- coding: utf-8 -*-
"""诊断 SCL9 在 6/9 交易日 9:30-10:35 区间的笔和线段划分"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE

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
bi_list = kl_list.bi_list
seg_list = kl_list.seg_list

print("=" * 90)
print(f"总笔数: {len(bi_list)}, 总线段数: {len(seg_list)}")
print("=" * 90)

# 打印 6/9 附近的笔（笔130-160）
print("\n--- 6/9 附近笔 (130-160) ---")
for bi in bi_list[130:161]:
    b_t = bi.get_begin_klu().time.to_str()
    e_t = bi.get_end_klu().time.to_str()
    print(f"笔{bi.idx}: {b_t} -> {e_t}  {'UP' if bi.is_up() else 'DOWN'}  "
          f"begin={bi.get_begin_val():.1f} end={bi.get_end_val():.1f}")

# 打印覆盖 6/9 的线段
print("\n--- 覆盖 6/9 的线段 ---")
for seg in seg_list:
    b_t = seg.start_bi.get_begin_klu().time.to_str()
    e_t = seg.end_bi.get_end_klu().time.to_str()
    # 线段包含笔130-160 区间
    if seg.end_bi.idx >= 130 and seg.start_bi.idx <= 160:
        print(f"线段{seg.idx}: 笔{seg.start_bi.idx}->笔{seg.end_bi.idx}  "
              f"{b_t} -> {e_t}  {'UP' if seg.dir == 1 else 'DOWN'}  "
              f"begin={seg.start_bi.get_begin_val():.1f} end={seg.end_bi.get_end_val():.1f}  sure={seg.is_sure}")

# 打印每根笔的 parent_seg 归属
print("\n--- 笔130-160 的线段归属 ---")
for bi in bi_list[130:161]:
    ps = bi.parent_seg
    ps_str = f"线段{ps.idx}" if ps else "无"
    b_t = bi.get_begin_klu().time.to_str()
    e_t = bi.get_end_klu().time.to_str()
    print(f"笔{bi.idx}: {b_t}->{e_t} {'UP' if bi.is_up() else 'DOWN'} 归属:{ps_str}")
