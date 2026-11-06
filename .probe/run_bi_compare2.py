# -*- coding: utf-8 -*-
"""对比不同参数下笔的划分序列是否一致（用 SequenceMatcher 算相同笔的比例）"""
import sys, os, difflib
ROOT = r"C:\Users\q8369\Documents\ChatGPT\chan.py-main"
sys.path.insert(0, ROOT)
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, AUTYPE

files = ["A111.txt", "CUL9.txt", "SCL9.txt"]
combos = [
    ("new+half(GUI)", {"bi_strict": False, "bi_fx_check": "half"}),
    ("new+loss", {"bi_strict": False, "bi_fx_check": "loss"}),
    ("old+loss", {"bi_strict": True, "bi_fx_check": "loss"}),
    ("old+strict", {"bi_strict": True, "bi_fx_check": "strict"}),
]


def run(path, cf):
    cfg = {"trigger_step": False, "print_warning": False}
    cfg.update(cf)
    conf = CChanConfig(cfg)
    chan = CChan(code=path, data_src="custom:TDX_TXT_API.TDX_TXT_API",
                 lv_list=[KL_TYPE.K_1M], config=conf, autype=AUTYPE.NONE)
    kl = chan[KL_TYPE.K_1M]
    seq = [(bi.get_begin_klu().idx, bi.get_end_klu().idx) for bi in kl.bi_list if bi.is_sure]
    return seq


def cmp(name_a, a, name_b, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ratio = sm.ratio()
    matched = sum(bl.size for bl in sm.get_matching_blocks())
    print("  %-14s vs %-14s : n=%4d/%4d  same_bi=%4d  ratio=%.3f"
          % (name_a, name_b, len(a), len(b), matched, ratio))


for f in files:
    path = os.path.join(ROOT, f)
    print("=" * 78)
    print("FILE:", f)
    seqs = {}
    for name, cf in combos:
        seqs[name] = run(path, cf)
        print("  %-14s n=%d" % (name, len(seqs[name])))
    cmp("new+half(GUI)", seqs["new+half(GUI)"], "new+loss", seqs["new+loss"])
    cmp("new+loss", seqs["new+loss"], "old+loss", seqs["old+loss"])
    cmp("new+half(GUI)", seqs["new+half(GUI)"], "old+strict", seqs["old+strict"])
    sys.stdout.flush()
print("ALL DONE")
