# -*- coding: utf-8 -*-
"""GUI 端到端测试：用 GUI 自己的配置和导出函数，把 10 秒数据的线段映射为 5 分钟公式。"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
import App.ashare_bsp_scanner_gui as gui_mod
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, AUTYPE
from DataAPI.TDX_TXT_API import TDX_TXT_API

app = QApplication([])
gui = gui_mod.AkshareGUI()
print("GUI_OK map_combo=", [gui.map_period_combo.itemText(i) for i in range(gui.map_period_combo.count())])
print("GUI_OK btn=", gui.map_export_btn.text())

TXT = r"C:\Users\q8369\Desktop\RML9.txt"
conf = CChanConfig({
    "trigger_step": False, "print_warning": False,
    "bi_strict": False, "bi_fx_check": "loss", "bi_end_is_peak": False,
})
chan = CChan(code=TXT, begin_time="2026-09", data_src="custom:TDX_TXT_API.TDX_TXT_API",
             lv_list=[KL_TYPE.K_1M], config=conf, autype=AUTYPE.NONE)
kl = chan[0]
gui.chan = chan
print("KLC", len(kl.lst), "BI", len(list(kl.bi_list)), "SEG", len(kl.seg_list))

# 自己聚合 5 分钟桶，验证映射命中
klus = []
for klc in kl.lst:
    klus.extend(klc.lst)
klus.sort(key=lambda k: k.idx)
PERIOD = 5


def plabel(t, pm):
    sec = t.hour * 3600 + t.minute * 60 + (getattr(t, "second", 0) or 0)
    ps = pm * 60
    lab = sec if sec % ps == 0 else ((sec // ps) + 1) * ps
    if lab >= 86400:
        lab -= 86400
    return lab // 3600, (lab % 3600) // 60


buckets = set()
for k in klus:
    t = k.time
    h, m = plabel(t, PERIOD)
    buckets.add((t.year, t.month, t.day, h, m))
print("BUCKETS", len(buckets))

miss = 0
for seg in kl.seg_list:
    for klu in (seg.start_bi.get_begin_klu(), seg.end_bi.get_end_klu()):
        t = klu.time
        h, m = plabel(t, PERIOD)
        if (t.year, t.month, t.day, h, m) not in buckets:
            miss += 1
print("ENDPOINT_BUCKET_MISS", miss)

out = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\rml9_5m.tni"
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: print("CRITICAL", a[2] if len(a) > 2 else a))
gui.map_period_combo.setCurrentIndex(0)  # 5 分钟
gui.export_tdx_seg_formula_mapped()
print("WROTE", os.path.exists(out), os.path.getsize(out) if os.path.exists(out) else 0)
if os.path.exists(out):
    content = open(out, encoding="gbk").read()
    lines = content.splitlines()
    print("HEADER:")
    for l in lines[:8]:
        print("   ", l)
    draws = [l for l in lines if l.startswith("DRAWLINE(")]
    bad_sec = [l for l in draws if "TIME2=" in l]
    print("DRAWLINE_CNT", len(draws), "TIME2_LEFT", len(bad_sec))
    for l in draws[:4]:
        print("   ", l)
    # 文件名应以 _5m 结尾
    print("FILENAME", os.path.basename(out))
    os.remove(out)
