# -*- coding: utf-8 -*-
"""追踪 can_make_bi 在 7/23 9:30-10:35 区间的判断"""
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

from Bi.BiList import CBiList
orig_can_make_bi = CBiList.can_make_bi

def traced_can_make_bi(self, klc, last_end, for_virtual=False):
    t = klc.lst[0].time.to_str()
    if t.startswith("2026/07/23") and "09:3" <= t[11:] <= "10:35":
        # 手动计算各条件
        satisify_span = self.satisfy_bi_span(klc, last_end)
        fx_valid = last_end.check_fx_valid(klc, self.config.bi_fx_check, for_virtual)
        end_peak = end_is_peak(last_end, klc)
        print(f"[can_make_bi] klc={t} fx={klc.fx} last_end={last_end.lst[0].time.to_str()} fx={last_end.fx} "
              f"span={satisify_span} fx_valid={fx_valid} end_is_peak={end_peak}")
    return orig_can_make_bi(self, klc, last_end, for_virtual)

from Bi.BiList import end_is_peak
CBiList.can_make_bi = traced_can_make_bi

chan = CChan(code="SCL9.txt", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=config)
chan.load()
