# -*- coding: utf-8 -*-
"""诊断：追踪 find_revert_fx 在 999999 数据上的调用"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE, BI_DIR
from ChanConfig import CChanConfig
from Seg.EigenFX import CEigenFX

_orig_find_revert_fx = CEigenFX.find_revert_fx
_orig_add = CEigenFX.add

def traced_add(self, bi):
    r = _orig_add(self, bi)
    print(f"    [add] bi{bi.idx} ({bi.dir.name}) -> fx={r} | ele={self}")
    return r

def traced_find_revert_fx(self, bi_list, begin_idx, thred_value, break_thred, outer_dir=None, outer_thred_value=None):
    print(f"  find_revert_fx: begin_idx={begin_idx}, thred_value={thred_value:.2f}, break_thred={break_thred:.2f}, outer_dir={outer_dir}, outer_thred_value={outer_thred_value}")
    r = _orig_find_revert_fx(self, bi_list, begin_idx, thred_value, break_thred, outer_dir, outer_thred_value)
    print(f"  find_revert_fx -> {r}")
    return r

CEigenFX.find_revert_fx = traced_find_revert_fx
CEigenFX.add = traced_add

def main():
    file_path = r"C:\Users\q8369\Desktop\999999.txt"
    config = CChanConfig({
        "bi_strict": True,
        "bi_fx_check": "half",
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": "1,1p,2,2s,3a,3b",
        "print_warning": False,
        "zs_algo": "normal",
        "cal_bi_zs": False,
        "cal_bi_bsp": False,
    })
    chan = CChan(
        code=file_path,
        begin_time="2024-09",
        data_src="custom:TDX_TXT_API.TDX_TXT_API",
        lv_list=[KL_TYPE.K_1M],
        config=config,
        autype=AUTYPE.NONE,
    )
    kl_list = chan[0]
    seg_list = kl_list.seg_list
    print("=" * 120)
    print("线段列表:")
    for seg in seg_list:
        sb = seg.start_bi
        eb = seg.end_bi
        print(f"seg{seg.idx}: {seg.dir.name} bi{sb.idx}->bi{eb.idx} | reason={seg.reason}")

if __name__ == "__main__":
    main()
