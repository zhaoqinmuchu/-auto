# -*- coding: utf-8 -*-
"""综合追踪 update_bi_sure 在 7/23 9:30-10:35 区间的每一步判断"""
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

from Bi.BiList import CBiList, end_is_peak
orig_update_bi_sure = CBiList.update_bi_sure

def traced_update_bi_sure(self, klc):
    t = klc.lst[0].time.to_str()
    if t.startswith("2026/07/23") and "09:3" <= t[11:] <= "10:35":
        last_end_str = f"{self.last_end.lst[0].time.to_str()}({self.last_end.fx})" if self.last_end else "None"
        # 手动计算 can_make_bi (for_virtual=False)
        if self.last_end is not None and klc.fx != FX_TYPE.UNKNOWN and klc.fx != self.last_end.fx:
            span = self.satisfy_bi_span(klc, self.last_end)
            fx_v = self.last_end.check_fx_valid(klc, self.config.bi_fx_check, False)
            ep = end_is_peak(self.last_end, klc)
            cmb = span and fx_v and ep
            print(f"[update_bi_sure] klc={t}({klc.fx}) last_end={last_end_str} "
                  f"span={span} fx_valid={fx_v} end_is_peak={ep} => can_make_bi={cmb}")
        else:
            print(f"[update_bi_sure] klc={t}({klc.fx}) last_end={last_end_str} (同型或None)")
        ret = orig_update_bi_sure(self, klc)
        if ret:
            if len(self.bi_list):
                lb = self.bi_list[-1]
                print(f"    -> 新笔{lb.idx}: {lb.get_begin_klu().time.to_str()}->{lb.get_end_klu().time.to_str()} "
                      f"{'UP' if lb.is_up() else 'DOWN'} begin={lb.get_begin_val():.1f} end={lb.get_end_val():.1f}")
        return ret
    return orig_update_bi_sure(self, klc)

CBiList.update_bi_sure = traced_update_bi_sure

chan = CChan(code="SCL9.txt", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=config)
chan.load()

kl_list = chan[0]
print("\n--- 最终 7/23 9:30-10:35 笔 ---")
for bi in kl_list.bi_list:
    b_t = bi.get_begin_klu().time.to_str()
    if b_t.startswith("2026/07/23") and "09:3" <= b_t[11:] <= "10:35":
        e_t = bi.get_end_klu().time.to_str()
        print(f"笔{bi.idx}: {b_t} -> {e_t}  {'UP' if bi.is_up() else 'DOWN'}  "
              f"begin={bi.get_begin_val():.1f} end={bi.get_end_val():.1f}")
