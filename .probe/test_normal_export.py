# -*- coding: utf-8 -*-
"""回归测试：原有"导出当前周期线段公式"按钮行为不变（AUL9 5分钟数据）。"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
import App.ashare_bsp_scanner_gui as gui_mod
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import KL_TYPE, AUTYPE

app = QApplication([])
gui = gui_mod.AkshareGUI()
conf = CChanConfig({
    "trigger_step": False, "print_warning": False,
    "bi_strict": False, "bi_fx_check": "loss", "bi_end_is_peak": False,
})
chan = CChan(code=r"C:\Users\q8369\Desktop\AUL9.txt", begin_time="2026-10",
             data_src="custom:TDX_TXT_API.TDX_TXT_API", lv_list=[KL_TYPE.K_1M],
             config=conf, autype=AUTYPE.NONE)
gui.chan = chan
print("KLC", len(chan[0].lst), "SEG", len(chan[0].seg_list))
out = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\aul9_normal.tni"
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: print("CRITICAL", a[2] if len(a) > 2 else a))
gui.export_tdx_seg_formula()
print("WROTE", os.path.exists(out))
if os.path.exists(out):
    content = open(out, encoding="gbk").read()
    lines = content.splitlines()
    print("HEADER:")
    for l in lines[:6]:
        print("   ", l)
    draws = [l for l in lines if l.startswith("DRAWLINE(")]
    print("DRAWLINE_CNT", len(draws))
    for l in draws[:3]:
        print("   ", l)
    os.remove(out)
