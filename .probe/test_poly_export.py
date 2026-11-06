# -*- coding: utf-8 -*-
"""离屏测试：GUI 折线版导出（不弹窗、不写仓库文件，只写临时目录）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = r"C:\Users\q8369\Documents\ChatGPT\chan.py-main"
TMP = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

from Common.CEnum import AUTYPE, KL_TYPE  # noqa: E402
from Chan import CChan  # noqa: E402
import App.ashare_bsp_scanner_gui as gui  # noqa: E402

CASES = [
    ("AUL9_5min", r"C:\Users\q8369\Desktop\AUL9.txt", "2026-10"),
    ("RML9_10s", r"C:\Users\q8369\Desktop\RML9.txt", None),
]

app = QApplication([])
g = gui.AkshareGUI()

# 屏蔽弹窗
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
QMessageBox.information = staticmethod(lambda *a, **k: None)

print("COMBO:", [g.map_period_combo.itemText(i) for i in range(g.map_period_combo.count())])
print("POLY_BTN:", g.poly_export_btn.text())

for name, path, begin_time in CASES:
    out_path = os.path.join(TMP, f"poly_{name}.tni")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, _p=out_path, **k: (_p, "tni"))
    cfg = g.get_chan_config()
    try:
        chan = CChan(
            code=path,
            begin_time=begin_time,
            data_src="custom:TDX_TXT_API.TDX_TXT_API",
            lv_list=[KL_TYPE.K_1M],
            config=cfg,
            autype=AUTYPE.NONE,
        )
    except Exception as e:
        print(f"[{name}] CHAN_ERR: {type(e).__name__}: {e}")
        continue
    g.chan = chan
    segs = chan[0].seg_list
    print(f"[{name}] KLC={len(chan[0].lst)} BI={len(chan[0].bi_list)} SEG={len(segs)}")
    for seg in segs:
        print(
            f"    seg{seg.idx} {'UP' if seg.is_up() else 'DN'} "
            f"{'sure' if seg.is_sure else 'unsure'} "
            f"{seg.start_bi.get_begin_klu().time.to_str()} {seg.start_bi.get_begin_val():.2f} -> "
            f"{seg.end_bi.get_end_klu().time.to_str()} {seg.end_bi.get_end_val():.2f}"
        )
    try:
        g.export_tdx_polyline_formula()
    except Exception as e:
        print(f"[{name}] EXPORT_ERR: {type(e).__name__}: {e}")
        continue
    if not os.path.exists(out_path):
        print(f"[{name}] NO_FILE")
        continue
    txt = open(out_path, "r", encoding="gbk", errors="ignore").read()
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    ploy = [ln for ln in lines if ln.upper().startswith("PLOYLINE")]
    ifs = [ln for ln in lines if ":=" in ln and "IF(" in ln.upper()]
    print(f"[{name}] FILE_BYTES={os.path.getsize(out_path)} LINES={len(lines)} IF_STMTS={len(ifs)} PLOYLINE={len(ploy)}")
    print(f"[{name}] HEAD:")
    for ln in lines[:8]:
        print("    " + ln)
    print(f"[{name}] TAIL:")
    for ln in lines[-4:]:
        print("    " + ln)
    print(f"[{name}] PLOYLINE_LINES: {ploy}")

print("DONE")
