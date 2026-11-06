# -*- coding: utf-8 -*-
"""诊断：打印 bi 列表的日期和值，映射到用户报告的时间戳"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from Common.CEnum import AUTYPE, KL_TYPE
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
    bi_list = kl_list.bi_list
    print("=" * 120)
    print("笔列表:")
    for bi in bi_list:
        b = bi.begin_klc[0].time
        e = bi.end_klc[-1].time
        print(f"bi{bi.idx}: {bi.dir.name} | {b} ({bi.get_begin_val():.2f}) -> {e} ({bi.get_end_val():.2f})")

if __name__ == "__main__":
    main()
