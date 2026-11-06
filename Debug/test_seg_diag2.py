# -*- coding: utf-8 -*-
"""诊断：打印 999999 数据的线段划分结果"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE, BI_DIR
from ChanConfig import CChanConfig

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
    print("线段列表 (seg_list):")
    for seg in seg_list:
        sb = seg.start_bi
        eb = seg.end_bi
        sb_klu = sb.get_begin_klu()
        eb_klu = eb.get_end_klu()
        print(f"seg{seg.idx}: {seg.dir.name} bi{sb.idx}->bi{eb.idx} | {sb_klu.time} ({sb_klu.close}) -> {eb_klu.time} ({eb_klu.close}) | reason={seg.reason}")

if __name__ == "__main__":
    main()
