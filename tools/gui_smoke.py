"""Exercise the unmodified Qt GUI offscreen; does not automate or replace the live desktop app."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
import warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["MPLCONFIGDIR"] = str(args.output.parent / "mpl-cache")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore", message="Glyph .* missing from font")
    sys.path.insert(0, str(args.source.resolve()))
    from App import ashare_bsp_scanner_gui as gui
    from matplotlib.backend_bases import MouseEvent
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = gui.AkshareGUI()
    window.resize(1600, 900)
    window.show()
    app.processEvents()
    errors = []
    checks = []
    exports = []
    fixtures = args.output.parent / "gui-inputs"
    fixtures.mkdir(exist_ok=True)
    for label, start, delta in (("daily", datetime(2025, 1, 1), timedelta(days=1)),
                                ("seconds", datetime(2025, 12, 31, 23, 50), timedelta(seconds=5))):
        rows = ["时间\t开盘\t最高\t最低\t收盘\t成交量"]
        for i in range(480):
            stamp = start + delta * i
            clock = stamp.strftime("%Y/%m/%d") if label == "daily" else f"{stamp.day}/{stamp:%H:%M:%S}"
            price = 100 + 10 * math.sin(i / 9) + 4 * math.sin(i / 31)
            rows.append(f"{clock}\t{price:.2f}\t{price+1.5:.2f}\t{price-1.5:.2f}\t{price+0.3:.2f}\t1000")
        (fixtures / f"{label}.txt").write_text("\n".join(rows) + "\n", encoding="gbk")

    def critical(*values, **kwargs):
        errors.append(str(values[2] if len(values) > 2 else values))
        return gui.QMessageBox.StandardButton.Ok

    with patch.object(gui.QMessageBox, "critical", side_effect=critical), \
         patch.object(gui.QMessageBox, "question", return_value=gui.QMessageBox.StandardButton.No):
        with patch.object(gui.QFileDialog, "getOpenFileName", return_value=("", "")):
            window.import_local_txt()
        assert window.chan is None and window.analysis_thread is None
        checks.append("cancel_file_selection")
        with patch.object(gui.QFileDialog, "getOpenFileName", return_value=(str(fixtures / "seconds.txt"), "")), \
             patch.object(gui.QInputDialog, "getText", return_value=("2026-01", False)):
            window.import_local_txt()
        assert window.chan is None and window.analysis_thread is None
        checks.append("cancel_reference_month")
        with patch.object(gui.QInputDialog, "getText", return_value=("", True)):
            assert window._ask_ref_year_month() == datetime.now().strftime("%Y-%m")
        checks.append("blank_month_uses_current_month")

        cases = (("local_futures", args.samples.resolve() / "CUL9.txt", "2026-08"),
                 ("daily", fixtures / "daily.txt", "2026-01"),
                 ("seconds_cross_year", fixtures / "seconds.txt", "2026-01"))
        for label, path, month in cases:
            with patch.object(gui.QFileDialog, "getOpenFileName", return_value=(str(path.resolve()), "")), \
                 patch.object(gui.QInputDialog, "getText", return_value=(month, True)):
                window.import_btn.click()
            deadline = time.monotonic() + 90
            while window.analysis_thread.isRunning() and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(0.01)
            if window.analysis_thread.isRunning():
                raise TimeoutError(f"Analysis thread timed out: {label}")
            app.processEvents()
            assert not errors, errors
            assert window.chan is not None and window.analyze_btn.isEnabled()
            assert window.chan.code == str(path.resolve())
            assert window.canvas.figure.axes
            units = list(window.chan[0].klu_iter())
            assert units
            if label == "daily":
                assert window.chan[0].kl_type.name == "K_DAY"
            if label == "seconds_cross_year":
                assert {u.time.year for u in units} == {2025, 2026}
            checks.append(f"import_and_draw_{label}")
            export_path = args.output.parent / f"{args.output.stem}-{label}.tni"
            if len(window.chan[0].seg_list):
                with patch.object(gui.QFileDialog, "getSaveFileName", return_value=(str(export_path.resolve()), "")):
                    window.export_btn.click()
                assert export_path.is_file() and not errors, errors
                content = export_path.read_text(encoding="gbk")
                assert "DRAWLINE(" in content
                if label == "seconds_cross_year":
                    assert "TIME2=" in content
                exports.append({"case": label, "sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
                                "drawlines": content.count("DRAWLINE("), "segments": len(window.chan[0].seg_list)})
                checks.append(f"export_formula_{label}")
            else:
                raise AssertionError(f"Fixture has no segments, cannot check export: {label}")

        for attribute in ("plot_kline_cb", "plot_bi_cb", "plot_seg_cb", "plot_zs_cb", "plot_bsp_cb", "plot_macd_cb"):
            box = getattr(window, attribute)
            old = box.isChecked()
            box.setChecked(not old)
            window.refresh_chart()
            box.setChecked(old)
            window.refresh_chart()
            assert not errors, errors
            checks.append(f"toggle_{attribute}")
        window.canvas.draw()
        axis = window.canvas.figure.axes[0]
        before = tuple(axis.get_xlim())
        px, py = axis.transData.transform((sum(before) / 2, sum(axis.get_ylim()) / 2))
        event = MouseEvent("scroll_event", window.canvas, px, py, button="up", step=1)
        window.canvas.callbacks.process("scroll_event", event)
        app.processEvents()
        assert tuple(axis.get_xlim()) != before
        checks.append("scroll_zoom")
        before = tuple(axis.get_xlim())
        px, py = axis.transData.transform((sum(before) / 2, sum(axis.get_ylim()) / 2))
        for kind, x in (("button_press_event", px), ("motion_notify_event", px + 50), ("button_release_event", px + 50)):
            window.canvas.callbacks.process(kind, MouseEvent(kind, window.canvas, x, py, button=1))
        app.processEvents()
        assert tuple(axis.get_xlim()) != before
        checks.append("drag_pan")
        window.canvas.figure.savefig(args.output.with_suffix(".png"), dpi=100)
        assert not errors, errors
    window.close()
    app.processEvents()
    report = {"mode": "Qt offscreen with mocked file/month dialogs; no native desktop interaction",
              "status": "PASS", "checks": checks, "exports": exports}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} GUI checks; report: {args.output}", flush=True)


if __name__ == "__main__":
    main()
