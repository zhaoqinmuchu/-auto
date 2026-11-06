# -*- coding: utf-8 -*-
"""对比不同画笔参数组合在真实数据上的笔数差异（HALF vs LOSS vs STRICT、新笔 vs 老笔）"""
import sys, os, time
ROOT = r"C:\Users\q8369\Documents\ChatGPT\chan.py-main"
sys.path.insert(0, ROOT)
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, AUTYPE

files = ["A111.txt", "CUL9.txt", "SCL9.txt"]
combos = [
    ("GUI新笔+HALF", {"bi_strict": False, "bi_fx_check": "half"}),
    ("新笔+LOSS", {"bi_strict": False, "bi_fx_check": "loss"}),
    ("新笔+STRICT", {"bi_strict": False, "bi_fx_check": "strict"}),
    ("新笔+TOTALLY", {"bi_strict": False, "bi_fx_check": "totally"}),
    ("老笔+STRICT", {"bi_strict": True, "bi_fx_check": "strict"}),
    ("老笔+LOSS", {"bi_strict": True, "bi_fx_check": "loss"}),
]

for f in files:
    path = os.path.join(ROOT, f)
    if not os.path.exists(path):
        print("MISSING", path)
        continue
    print("=" * 78)
    print("FILE:", f)
    for name, cf in combos:
        cfg = {"trigger_step": False, "print_warning": False}
        cfg.update(cf)
        conf = CChanConfig(cfg)
        t0 = time.time()
        chan = CChan(code=path, data_src="custom:TDX_TXT_API.TDX_TXT_API",
                     lv_list=[KL_TYPE.K_1M], config=conf, autype=AUTYPE.NONE)
        kl = chan[KL_TYPE.K_1M]
        bis = kl.bi_list
        n = len(bis)
        tot = 0
        sure = 0
        for bi in bis:
            tot += bi.get_klu_cnt()
            if bi.is_sure:
                sure += 1
        print("%-12s 笔数=%5d 确定笔=%4d 均原始K线/笔=%6.2f 合并K线=%5d 耗时=%5.1fs"
              % (name, n, sure, tot / max(n, 1), len(kl.lst), time.time() - t0))
    sys.stdout.flush()
print("ALL DONE")
