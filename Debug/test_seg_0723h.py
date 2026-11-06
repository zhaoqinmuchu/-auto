# -*- coding: utf-8 -*-
"""追踪 check_fx_valid 在 7/23 9:30-10:35 区间的实际计算值 + pre/next"""
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

from KLine.KLine import CKLine
orig_check_fx_valid = CKLine.check_fx_valid

def traced_check_fx_valid(self, item2, method, for_virtual=False):
    t = item2.lst[0].time.to_str()
    if t.startswith("2026/07/23") and "09:3" <= t[11:] <= "10:35":
        pre_t = item2.pre.lst[0].time.to_str() if item2.pre else "None"
        next_t = self.next.lst[0].time.to_str() if self.next else "None"
        # 手动复现 HALF 逻辑
        if self.fx == FX_TYPE.TOP:
            item2_high = max([item2.pre.high, item2.high])
            self_low = min([self.low, self.next.low])
            res = self.high > item2_high and item2.low < self_low
            print(f"[fx_valid] for_virtual={for_virtual} self={self.lst[0].time.to_str()}({self.fx}) "
                  f"item2={t}({item2.fx}) pre={pre_t} next={next_t} "
                  f"self.high={self.high} item2_high={item2_high} item2.low={item2.low} self_low={self_low} -> {res}")
        elif self.fx == FX_TYPE.BOTTOM:
            item2_low = min([item2.pre.low, item2.low])
            cur_high = max([self.high, self.next.high])
            res = self.low < item2_low and item2.high > cur_high
            print(f"[fx_valid] for_virtual={for_virtual} self={self.lst[0].time.to_str()}({self.fx}) "
                  f"item2={t}({item2.fx}) pre={pre_t} next={next_t} "
                  f"self.low={self.low} item2_low={item2_low}(pre.low={item2.pre.low},item2.low={item2.low}) "
                  f"item2.high={item2.high} cur_high={cur_high}(self.high={self.high},next.high={self.next.high}) -> {res}")
    return orig_check_fx_valid(self, item2, method, for_virtual)

CKLine.check_fx_valid = traced_check_fx_valid

chan = CChan(code="SCL9.txt", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=config)
chan.load()
