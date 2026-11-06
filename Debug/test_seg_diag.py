# -*- coding: utf-8 -*-
"""诊断：打印 999999 数据 2024/09/18 之后所有笔的详细信息"""
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
    bi_list = kl_list.bi_list

    print("=" * 120)
    print("笔列表 (bi_list) - 从 bi57 开始:")
    for bi in bi_list:
        if bi.idx < 57:
            continue
        b_klu = bi.get_begin_klu()
        e_klu = bi.get_end_klu()
        print(f"bi{bi.idx}: {bi.dir.name} {b_klu.time} ({b_klu.close}) -> {e_klu.time} ({e_klu.close}) | high={e_klu.high:.2f} low={e_klu.low:.2f}")

if __name__ == "__main__":
    main()
