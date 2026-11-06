# -*- coding: utf-8 -*-
"""调试：线段划分第二种情况（有缺口）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE, BI_DIR
from ChanConfig import CChanConfig
from Seg.EigenFX import CEigenFX

# 追踪 find_revert_fx
_orig_find_revert_fx = CEigenFX.find_revert_fx
def traced_find_revert_fx(self, bi_list, begin_idx, thred_value, break_thred, outer_dir=None, outer_thred_value=None):
    if outer_dir is None:
        outer_dir = self.dir
        outer_thred_value = thred_value
    print(f"  [find_revert_fx] self.dir={self.dir.name} begin_idx={begin_idx} thred_value={thred_value:.2f} outer_dir={outer_dir.name} outer_thred_value={outer_thred_value:.2f}")
    result = _orig_find_revert_fx(self, bi_list, begin_idx, thred_value, break_thred, outer_dir, outer_thred_value)
    print(f"  [find_revert_fx] -> {result}")
    return result
CEigenFX.find_revert_fx = traced_find_revert_fx

# 追踪 add
_orig_add = CEigenFX.add
def traced_add(self, bi):
    result = _orig_add(self, bi)
    ele_str = []
    for e in self.ele:
        if e is None:
            ele_str.append("None")
        else:
            ele_str.append(f"[{','.join(str(b.idx) for b in e.lst)}]")
    print(f"    add(bi{bi.idx}) -> {result} | ele={' '.join(ele_str)}")
    return result
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
    bi_list = kl_list.bi_list
    seg_list = kl_list.seg_list

    print("=" * 100)
    print("线段列表 (seg_list):")
    for seg in seg_list:
        sb = seg.start_bi
        eb = seg.end_bi
        sb_klu = sb.get_begin_klu()
        eb_klu = eb.get_end_klu()
        print(f"seg{seg.idx}: {seg.dir.name} bi[{sb.idx}->{eb.idx}] {sb_klu.time} ({sb_klu.close}) -> {eb_klu.time} ({eb_klu.close}) | sure={seg.is_sure}")

if __name__ == "__main__":
    main()
