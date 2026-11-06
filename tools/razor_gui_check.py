r"""Offscreen Qt acceptance check for the Razor GUI (App/ashare_bsp_scanner_gui.py).

Instantiates the GUI with QT_QPA_PLATFORM=offscreen, runs every check stated in the
Razor acceptance task, writes a JSON report with per-check PASS/FAIL, and exits 0 only
when every check passed. No native desktop interaction, no network unless --network.

Checks:
  scan_removal     - scanning UI/attributes/module symbols/callbacks and "扫描" window text gone
  preserved        - widgets that must survive the Razor edit
  chan_config      - get_chan_config() defaults unchanged, bi_strict hard False
  plot_config      - get_plot_config() defaults unchanged
  period_options   - 6 periods and their tencent/baostock data-source mapping
  dialogs          - cancel file picker / cancel reference month / blank month = current month
  import           - local TXT import for CUL9 futures / daily fixture / cross-year seconds
  export           - .tni export: GBK, DRAWLINE, seconds TIME2, sha256 vs gui-before.json
  interaction      - scroll zoom, left-drag pan, right-box zoom, double-click restore,
                     crosshair, six display toggles
  network          - opt-in single-stock baostock daily analysis (600000, days=30)

Run:
  .\.venv\Scripts\python.exe -B tools\razor_gui_check.py --output .\.local-validation\razor\gui-after.json
  .\.venv\Scripts\python.exe -B tools\razor_gui_check.py --precheck --output .\.local-validation\razor\gui-razor-precheck.json
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback
import warnings


ROOT = Path(__file__).resolve().parent.parent

# Attributes that must no longer exist after the Razor edit.
SCAN_ATTRS = (
    "scan_btn", "stop_btn", "progress_bar", "progress_label", "stock_table",
    "clear_list_btn", "log_text", "scan_thread", "stock_cache", "bi_strict_cb",
)
SCAN_MODULE_SYMBOLS = (
    "get_tradable_stocks", "ScanThread", "start_scan", "stop_scan",
    "on_scan_progress", "on_buy_point_found", "on_scan_finished", "on_stock_clicked",
    "clear_stock_list", "bi_strict_cb",
)

EXPECTED_CHAN_CONFIG = {
    "bi_strict": False,
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
}

EXPECTED_PLOT_CONFIG = {
    "plot_kline": True,
    "plot_kline_combine": True,
    "plot_bi": True,
    "plot_seg": True,
    "plot_zs": False,
    "plot_segzs": True,
    "plot_macd": False,
    "plot_bsp": False,
    "plot_segbsp": True,
}

EXPECTED_PERIODS = (
    ("1分钟", "K_1M", "tencent"),
    ("5分钟", "K_5M", "tencent"),
    ("15分钟", "K_15M", "tencent"),
    ("30分钟", "K_30M", "tencent"),
    ("60分钟", "K_60M", "tencent"),
    ("日线", "K_DAY", "baostock"),
)

# label -> (fixture path relative to <output parent>/gui-inputs or sample dir, reference month,
#           expected kl_type, expected raw kline count, expected years, export case name)
IMPORT_CASES = (
    ("local_futures", "CUL9.txt", "2026-08", "K_1M", 10500, {2026}, "local_futures"),
    ("daily", "daily.txt", "2026-01", "K_DAY", 480, {2025, 2026}, "daily"),
    ("seconds_cross_year", "seconds.txt", "2026-01", "K_1M", 480, {2025, 2026}, "seconds_cross_year"),
)


def json_safe(value):
    """Make a value JSON-serializable (inf/nan/Path become strings)."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if math.isnan(value):
            return "NaN"
    if isinstance(value, Path):
        return str(value)
    return value


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_fixtures(fixtures):
    """Recreate the two fixtures exactly as tools/gui_smoke.py does (GBK, 480 rows)."""
    fixtures.mkdir(parents=True, exist_ok=True)
    for label, start, delta in (("daily", datetime(2025, 1, 1), timedelta(days=1)),
                                ("seconds", datetime(2025, 12, 31, 23, 50), timedelta(seconds=5))):
        rows = ["时间\t开盘\t最高\t最低\t收盘\t成交量"]
        for i in range(480):
            stamp = start + delta * i
            clock = stamp.strftime("%Y/%m/%d") if label == "daily" else f"{stamp.day}/{stamp:%H:%M:%S}"
            price = 100 + 10 * math.sin(i / 9) + 4 * math.sin(i / 31)
            rows.append(f"{clock}\t{price:.2f}\t{price+1.5:.2f}\t{price-1.5:.2f}\t{price+0.3:.2f}\t1000")
        (fixtures / f"{label}.txt").write_text("\n".join(rows) + "\n", encoding="gbk")


def extract_chan_config(cfg):
    """Extract the pre-Razor GUI default dict out of a CChanConfig object."""
    b = cfg.bs_point_conf.b_conf
    return {
        "bi_strict": cfg.bi_conf.is_strict,
        "bi_fx_check": cfg.bi_conf.bi_fx_check.name.lower(),
        "trigger_step": cfg.trigger_step,
        "skip_step": cfg.skip_step,
        "divergence_rate": b.divergence_rate,
        "bsp2_follow_1": b.bsp2_follow_1,
        "bsp3_follow_1": b.bsp3_follow_1,
        "min_zs_cnt": b.min_zs_cnt,
        "bs1_peak": b.bs1_peak,
        "macd_algo": b.macd_algo.name.lower(),
        "bs_type": ",".join(t.value for t in b.target_types),
        "print_warning": cfg.print_warning,
        "zs_algo": cfg.zs_conf.zs_algo,
        "cal_bi_zs": cfg.cal_bi_zs,
        "cal_bi_bsp": cfg.cal_bi_bsp,
    }


def collect_window_texts(window, qt_widgets):
    """Every user-visible string on the window: titles, labels, buttons, headers, status."""
    entries = []

    def add(source, value):
        if isinstance(value, str) and value.strip():
            entries.append({"source": source, "text": value})

    add("window.windowTitle()", window.windowTitle())
    status_bar = getattr(window, "statusBar", None)
    if callable(status_bar):
        try:
            status_bar = status_bar()
        except Exception:
            status_bar = None
    if isinstance(status_bar, qt_widgets.QStatusBar):
        add("statusBar.currentMessage()", status_bar.currentMessage())
    for widget in window.findChildren(qt_widgets.QWidget):
        cls = type(widget).__name__
        for method in ("text", "windowTitle", "title", "placeholderText"):
            if hasattr(widget, method):
                try:
                    add(f"{cls}.{method}()", getattr(widget, method)())
                except Exception:
                    pass
        if isinstance(widget, qt_widgets.QTableWidget):
            for column in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(column)
                if item is not None:
                    add(f"QTableWidget.header[{column}]", item.text())
        if isinstance(widget, qt_widgets.QComboBox):
            for index in range(widget.count()):
                add(f"QComboBox.item[{index}]", widget.itemText(index))
    menu_bar = getattr(window, "menuBar", None)
    if callable(menu_bar):
        try:
            for action in menu_bar().actions():
                add("menuBar.action", action.text())
        except Exception:
            pass
    for toolbar in window.findChildren(qt_widgets.QToolBar):
        for action in toolbar.actions():
            add("toolbar.action", action.text())
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=ROOT, help="source tree to import (default: project root)")
    parser.add_argument("--output", type=Path, default=ROOT / ".local-validation" / "razor" / "gui-after.json")
    parser.add_argument("--samples", type=Path, default=ROOT, help="directory holding CUL9.txt (default: project root)")
    parser.add_argument("--gui-before", type=Path, default=ROOT / ".local-validation" / "razor" / "gui-before.json",
                        help="pre-Razor GUI report used for export sha256 comparison")
    parser.add_argument("--network", action="store_true", help="also run one bounded single-stock baostock daily analysis")
    parser.add_argument("--precheck", action="store_true", help="mark the report as the red-state pre-Razor check")
    parser.add_argument("--note", default="", help="free-text note recorded in the JSON report")
    parser.add_argument("--retry-delay", type=float, default=60.0,
                        help="seconds to wait before retrying a failed import/instantiation once (default 60)")
    args = parser.parse_args()

    started = time.time()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["MPLCONFIGDIR"] = str(output.parent / "mpl-cache")
    warnings.filterwarnings("ignore", message="Glyph .* missing from font")

    source = args.source.resolve()
    samples = args.samples.resolve()
    fixtures = output.parent / "gui-inputs"
    make_fixtures(fixtures)

    report = {
        "tool": "tools/razor_gui_check.py",
        "mode": "Qt offscreen with mocked file/month dialogs; no native desktop interaction",
        "phase": "precheck" if args.precheck else "post-razor",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "source": str(source),
        "samples": str(samples),
        "output": str(output),
        "gui_before": str(args.gui_before.resolve()),
        "network": args.network,
        "note": args.note,
        "checks": [],
        "exports": [],
    }
    checks = report["checks"]

    def record(name, group, status, detail=None):
        checks.append({"group": group, "name": name, "status": status, "detail": json_safe(detail)})
        line = f"{status} [{group}] {name}"
        if status != "PASS" and detail:
            line += f" :: {detail}"
        print(line, flush=True)

    def run(name, group, fn):
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - every check must be recorded, never crash the run
            record(name, group, "FAIL", f"{type(exc).__name__}: {exc}")
            return False
        record(name, group, "PASS", detail)
        return True

    # ---------------------------------------------------------------- reference data
    try:
        gui_before = json.loads(args.gui_before.read_text(encoding="utf-8"))
        expected_exports = {entry["case"]: entry for entry in gui_before.get("exports", [])}
        before_info = {"checks": len(gui_before.get("checks", [])), "exports": sorted(expected_exports)}
    except Exception as exc:  # noqa: BLE001
        gui_before = None
        expected_exports = {}
        before_info = {"error": f"{type(exc).__name__}: {exc}"}
    report["gui_before_reference"] = before_info

    # ---------------------------------------------------------------- import + window
    gui = None
    window = None
    app = None
    try:
        sys.path.insert(0, str(source))

        def import_gui_module():
            for key in [key for key in list(sys.modules) if key == "App.ashare_bsp_scanner_gui"]:
                del sys.modules[key]
            importlib.invalidate_caches()
            module = importlib.import_module("App.ashare_bsp_scanner_gui")
            return module

        try:
            gui = import_gui_module()
            gui_import_error = None
        except Exception as first:  # noqa: BLE001 - concurrent edit may be mid-write
            report["import_retry"] = {"first_error": f"{type(first).__name__}: {first}",
                                      "retry_delay_s": args.retry_delay}
            print(f"RETRY: import failed ({type(first).__name__}: {first}); waiting {args.retry_delay}s", flush=True)
            time.sleep(args.retry_delay)
            try:
                gui = import_gui_module()
                report["import_retry"]["status"] = "PASS on retry"
            except Exception as second:  # noqa: BLE001
                report["import_retry"]["status"] = f"FAIL on retry: {type(second).__name__}: {second}"
                report["import_retry"]["second_error"] = f"{type(second).__name__}: {second}"
                raise
        from matplotlib.backend_bases import MouseEvent
        from PyQt6 import QtWidgets
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        window = gui.AkshareGUI()
        window.resize(1600, 900)
        window.show()
        app.processEvents()
        report["window"] = {"title": window.windowTitle(), "size": [window.width(), window.height()]}
    except Exception as exc:  # noqa: BLE001
        report["fatal"] = f"GUI import/instantiation failed: {type(exc).__name__}: {exc}"
        report["fatal_traceback"] = traceback.format_exc()
        record("instantiate_gui", "bootstrap", "FAIL", report["fatal"])
        finalize(report, checks, started, output)
        return 1

    from unittest.mock import patch

    criticals = []
    warnings_seen = []

    def _critical(*values, **kwargs):
        criticals.append(str(values[2] if len(values) > 2 else values))
        return gui.QMessageBox.StandardButton.Ok

    def _warning(*values, **kwargs):
        warnings_seen.append(str(values[2] if len(values) > 2 else values))
        return gui.QMessageBox.StandardButton.Ok

    def clear_messages():
        criticals.clear()
        warnings_seen.clear()

    def ask_year_month(return_value):
        return patch.object(gui.QInputDialog, "getText", return_value=return_value)

    def open_file(return_value):
        return patch.object(gui.QFileDialog, "getOpenFileName", return_value=return_value)

    def save_file(return_value):
        return patch.object(gui.QFileDialog, "getSaveFileName", return_value=return_value)

    # ---------------------------------------------------------------- 1. scan removal
    def check_scan_attrs():
        present = [name for name in SCAN_ATTRS if hasattr(window, name)]
        assert not present, f"scan-only attributes still present: {present}"
        return {"absent": list(SCAN_ATTRS)}

    run("scan_attributes_absent", "scan_removal", check_scan_attrs)

    def check_scan_symbols():
        source_path = Path(gui.__file__).resolve()
        source_text = source_path.read_text(encoding="utf-8", errors="replace")
        found = []
        for name in SCAN_MODULE_SYMBOLS:
            for match in re.finditer(r"\b" + re.escape(name) + r"\b", source_text):
                line = source_text[:match.start()].count("\n") + 1
                found.append(f"{name}@{source_path.name}:{line}")
        module_attrs = [name for name in SCAN_MODULE_SYMBOLS if hasattr(gui, name)]
        assert not found and not module_attrs, f"scan symbols in source: {sorted(set(found))}; module attrs: {module_attrs}"
        return {"source": str(source_path), "searched": list(SCAN_MODULE_SYMBOLS)}

    run("scan_module_symbols_absent", "scan_removal", check_scan_symbols)

    def check_scan_window_text():
        entries = collect_window_texts(window, QtWidgets)
        report["window_texts"] = entries
        hits = [entry for entry in entries if "扫描" in entry["text"]]
        assert not hits, f"'扫描' still visible: {hits[:10]}"
        return {"texts_checked": len(entries)}

    run("scan_window_text_absent", "scan_removal", check_scan_window_text)

    def check_bi_strict_cb():
        assert not hasattr(window, "bi_strict_cb"), "bi_strict_cb still exists"
        return {"absent": True}

    run("bi_strict_cb_absent", "scan_removal", check_bi_strict_cb)

    # ---------------------------------------------------------------- 2. preserved widgets
    preserved = (
        ("code_input", lambda w: isinstance(w, QtWidgets.QLineEdit)),
        ("analyze_btn", lambda w: isinstance(w, QtWidgets.QPushButton)),
        ("period_combo", lambda w: isinstance(w, QtWidgets.QComboBox)),
        ("import_btn", lambda w: isinstance(w, QtWidgets.QPushButton)),
        ("export_btn", lambda w: isinstance(w, QtWidgets.QPushButton)),
        ("refresh_btn", lambda w: isinstance(w, QtWidgets.QPushButton)),
        ("plot_kline_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
        ("plot_bi_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
        ("plot_seg_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
        ("plot_zs_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
        ("plot_bsp_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
        ("plot_macd_cb", lambda w: isinstance(w, QtWidgets.QCheckBox)),
    )
    for attr, predicate in preserved:
        def check_attribute(attr=attr, predicate=predicate):
            assert hasattr(window, attr), f"missing widget attribute: {attr}"
            widget = getattr(window, attr)
            assert predicate(widget), f"{attr} has unexpected type {type(widget).__name__}"
            return {"type": type(widget).__name__}
        run(f"widget_{attr}", "preserved_widgets", check_attribute)

    def check_canvas():
        assert hasattr(window, "canvas"), "missing canvas"
        assert isinstance(window.canvas, gui.FigureCanvas), f"canvas type {type(window.canvas).__name__}"
        return {"type": type(window.canvas).__name__}

    run("widget_canvas", "preserved_widgets", check_canvas)

    def check_toolbar():
        assert hasattr(window, "toolbar"), "missing toolbar"
        assert isinstance(window.toolbar, gui.NavigationToolbar), f"toolbar type {type(window.toolbar).__name__}"
        return {"type": type(window.toolbar).__name__}

    run("widget_toolbar", "preserved_widgets", check_toolbar)

    # ---------------------------------------------------------------- 3. chan config
    def check_chan_config():
        actual = extract_chan_config(window.get_chan_config())
        mismatches = {key: {"expected": EXPECTED_CHAN_CONFIG[key], "actual": actual.get(key)}
                      for key in EXPECTED_CHAN_CONFIG if actual.get(key) != EXPECTED_CHAN_CONFIG[key]}
        assert not mismatches, f"get_chan_config defaults differ: {mismatches}"
        return {"config": actual}

    run("get_chan_config_default", "chan_config", check_chan_config)

    def check_bi_strict_always_false():
        actual = extract_chan_config(window.get_chan_config())
        assert actual["bi_strict"] is False, f"default bi_strict is {actual['bi_strict']!r}, expected False"
        if hasattr(window, "bi_strict_cb"):
            checkbox = window.bi_strict_cb
            old = checkbox.isChecked()
            try:
                checkbox.setChecked(True)
                forced = extract_chan_config(window.get_chan_config())
            finally:
                checkbox.setChecked(old)
            assert forced["bi_strict"] is False, (
                "bi_strict follows a checkbox (got True when checked); it must be hard-coded False")
            return {"bi_strict": False, "control": "bi_strict_cb present but ignored"}
        return {"bi_strict": False, "control": "removed"}

    run("get_chan_config_bi_strict_always_false", "chan_config", check_bi_strict_always_false)

    # ---------------------------------------------------------------- 4. plot config
    def check_plot_config():
        actual = window.get_plot_config()
        assert isinstance(actual, dict), f"get_plot_config returned {type(actual).__name__}"
        assert actual == EXPECTED_PLOT_CONFIG, f"get_plot_config differs: {actual}"
        return {"config": actual}

    run("get_plot_config_default", "plot_config", check_plot_config)

    # ---------------------------------------------------------------- 5. periods
    def check_period_options():
        options = gui.PERIOD_OPTIONS
        assert isinstance(options, (list, tuple)), f"PERIOD_OPTIONS type {type(options).__name__}"
        assert len(options) == 6, f"PERIOD_OPTIONS has {len(options)} entries, expected 6"
        actual = [(text, kl.name, data_src) for text, kl, data_src in options]
        expected = [tuple(item) for item in EXPECTED_PERIODS]
        assert actual == expected, f"PERIOD_OPTIONS mismatch: {actual}"
        combo_texts = [window.period_combo.itemText(i) for i in range(window.period_combo.count())]
        assert combo_texts == [text for text, _, _ in expected], f"period_combo items mismatch: {combo_texts}"
        for text, kl_name, data_src in expected:
            got_kl, got_src = gui.get_period_config(text)
            assert got_kl.name == kl_name and got_src == data_src, (
                f"get_period_config({text!r}) -> ({got_kl.name}, {got_src}), expected ({kl_name}, {data_src})")
        fallback_kl, fallback_src = gui.get_period_config("not-a-period")
        assert (fallback_kl.name, fallback_src) == ("K_DAY", "baostock"), (
            f"get_period_config fallback -> ({fallback_kl.name}, {fallback_src})")
        return {"options": actual, "combo": combo_texts, "fallback": ["K_DAY", "baostock"]}

    run("period_options_and_mapping", "period_options", check_period_options)

    # ---------------------------------------------------------------- 6. dialogs
    with patch.object(gui.QMessageBox, "critical", side_effect=_critical), \
         patch.object(gui.QMessageBox, "warning", side_effect=_warning), \
         patch.object(gui.QMessageBox, "question", return_value=gui.QMessageBox.StandardButton.No):

        def check_cancel_file_selection():
            clear_messages()
            with open_file(("", "")):
                window.import_local_txt()
            app.processEvents()
            assert window.chan is None, "chan was set even though the file picker was cancelled"
            assert window.analysis_thread is None, "analysis thread started although the file picker was cancelled"
            assert not criticals, criticals
            return {"chan": None, "analysis_thread": None}

        run("cancel_file_selection", "dialogs", check_cancel_file_selection)

        def check_cancel_reference_month():
            clear_messages()
            seconds_path = fixtures / "seconds.txt"
            with open_file((str(seconds_path.resolve()), "")), ask_year_month(("2026-01", False)):
                window.import_local_txt()
            app.processEvents()
            assert window.chan is None, "chan was set even though the month dialog was cancelled"
            assert window.analysis_thread is None, "analysis thread started although the month dialog was cancelled"
            assert not criticals, criticals
            return {"chan": None, "analysis_thread": None}

        run("cancel_reference_month", "dialogs", check_cancel_reference_month)

        def check_blank_month():
            clear_messages()
            expected = datetime.now().strftime("%Y-%m")
            with ask_year_month(("", True)):
                value = window._ask_ref_year_month()
            assert value == expected, f"blank month -> {value!r}, expected current month {expected!r}"
            return {"value": value, "current_month": expected}

        run("blank_month_uses_current_month", "dialogs", check_blank_month)

        # ------------------------------------------------------------ 7. local TXT imports + exports
        sample_missing = [label for label, relative, *_ in IMPORT_CASES
                          if relative == "CUL9.txt" and not (samples / relative).is_file()]

        def check_samples_available():
            assert (samples / "CUL9.txt").is_file(), f"sample missing: {samples / 'CUL9.txt'}"
            for name in ("daily.txt", "seconds.txt"):
                assert (fixtures / name).is_file(), f"fixture missing: {fixtures / name}"
            return {"samples": str(samples), "fixtures": str(fixtures)}

        run("fixtures_available", "import", check_samples_available)

        for label, relative, month, kl_name, raw_count, expected_years, export_case in IMPORT_CASES:
            path = (samples / relative) if relative == "CUL9.txt" else (fixtures / relative)
            resolved = path.resolve()

            def do_import(label=label, resolved=resolved, month=month, kl_name=kl_name,
                          raw_count=raw_count, expected_years=expected_years):
                clear_messages()
                with open_file((str(resolved), "")), ask_year_month((month, True)):
                    window.import_btn.click()
                deadline = time.monotonic() + 120
                while window.analysis_thread is not None and window.analysis_thread.isRunning() \
                        and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)
                if window.analysis_thread is not None and window.analysis_thread.isRunning():
                    raise TimeoutError(f"analysis thread timed out for {label}")
                app.processEvents()
                assert not criticals, criticals
                assert window.chan is not None, "chan is None after import"
                assert window.analyze_btn.isEnabled(), "analyze button not re-enabled after import"
                assert window.chan.code == str(resolved), f"chan.code {window.chan.code!r} != {str(resolved)!r}"
                assert window.canvas.figure.axes, "canvas figure has no axes after import"
                units = list(window.chan[0].klu_iter())
                assert units, "no raw klines parsed"
                assert len(units) == raw_count, f"raw kline count {len(units)}, expected {raw_count}"
                assert window.chan[0].kl_type.name == kl_name, (
                    f"kl_type {window.chan[0].kl_type.name}, expected {kl_name}")
                years = {unit.time.year for unit in units}
                assert years == expected_years, f"years {sorted(years)}, expected {sorted(expected_years)}"
                assert window.chan[0].seg_list, "no segments; export cannot be checked"
                return {"code": window.chan.code, "kl_type": kl_name, "raw_klines": len(units),
                        "years": sorted(years), "segments": len(window.chan[0].seg_list),
                        "first_time": units[0].time.to_str(), "last_time": units[-1].time.to_str()}

            imported = run(f"import_and_draw_{label}", "import", do_import)
            if not imported:
                continue

            def do_export(label=label, export_case=export_case):
                clear_messages()
                export_path = output.parent / f"{output.stem}-{label}.tni"
                if export_path.exists():
                    export_path.unlink()
                with save_file((str(export_path.resolve()), "")):
                    window.export_btn.click()
                app.processEvents()
                assert not criticals, criticals
                assert export_path.is_file(), f"export file not written: {export_path}"
                content = export_path.read_text(encoding="gbk")  # strict GBK decode
                assert "DRAWLINE(" in content, "DRAWLINE( missing from export"
                assert "DATE=" in content, "DATE= missing from export"
                if label == "seconds_cross_year":
                    assert "TIME2=" in content, "TIME2= missing from cross-year seconds export"
                drawlines = content.count("DRAWLINE(")
                segments = len(window.chan[0].seg_list)
                assert drawlines == segments, f"drawlines {drawlines} != segments {segments}"
                sha = sha256_file(export_path)
                expected = expected_exports.get(export_case)
                assert expected is not None, f"gui-before.json has no export record for {export_case!r}"
                assert sha == expected["sha256"], (
                    f"export sha256 {sha} != pre-Razor {expected['sha256']} ({export_case})")
                assert drawlines == expected["drawlines"], (
                    f"drawlines {drawlines} != pre-Razor {expected['drawlines']}")
                assert segments == expected["segments"], (
                    f"segments {segments} != pre-Razor {expected['segments']}")
                entry = {"case": export_case, "path": str(export_path), "sha256": sha,
                         "drawlines": drawlines, "segments": segments, "gbk": True,
                         "time2": "TIME2=" in content}
                report["exports"].append(entry)
                return entry

            run(f"export_formula_{label}", "export", do_export)

        # ------------------------------------------------------------ 8. chart interaction
        def current_axis():
            window.canvas.draw()
            assert window.canvas.figure.axes, "no axes on canvas"
            return window.canvas.figure.axes[0]

        def clear_crosshair():
            for line in (getattr(window, "_cross_vline", None), getattr(window, "_cross_hline", None)):
                if line is not None:
                    try:
                        line.remove()
                    except Exception:
                        pass
            text = getattr(window, "_cross_text", None)
            if text is not None:
                try:
                    text.remove()
                except Exception:
                    pass
            window._cross_vline = window._cross_hline = window._cross_text = None

        interaction_state = {}

        def check_scroll_zoom():
            axis = current_axis()
            interaction_state["initial_xlim"] = tuple(axis.get_xlim())
            before = tuple(axis.get_xlim())
            mid = ((before[0] + before[1]) / 2, (sum(axis.get_ylim()) / 2))
            px, py = axis.transData.transform(mid)
            event = MouseEvent("scroll_event", window.canvas, px, py, button="up", step=1)
            window.canvas.callbacks.process("scroll_event", event)
            app.processEvents()
            after = tuple(axis.get_xlim())
            assert after != before, "scroll wheel did not change xlim"
            assert (after[1] - after[0]) < (before[1] - before[0]) * 0.95, (
                f"scroll zoom did not narrow xlim: {before} -> {after}")
            interaction_state["zoomed_xlim"] = after
            return {"before": before, "after": after}

        run("scroll_zoom", "interaction", check_scroll_zoom)

        def check_drag_pan():
            axis = current_axis()
            before = tuple(axis.get_xlim())
            mid = ((before[0] + before[1]) / 2, sum(axis.get_ylim()) / 2)
            px, py = axis.transData.transform(mid)
            for kind, x, button in (("button_press_event", px, 1),
                                    ("motion_notify_event", px + 60, 1),
                                    ("button_release_event", px + 60, 1)):
                window.canvas.callbacks.process(
                    kind, MouseEvent(kind, window.canvas, x, py, button=button))
            app.processEvents()
            after = tuple(axis.get_xlim())
            assert after != before, "left-drag did not change xlim"
            assert abs((after[1] - after[0]) - (before[1] - before[0])) < (before[1] - before[0]) * 0.01, (
                f"drag changed the zoom range instead of panning: {before} -> {after}")
            assert after[0] < before[0], f"drag to the right did not pan the view left: {before} -> {after}"
            interaction_state["panned_xlim"] = after
            return {"before": before, "after": after}

        run("drag_pan", "interaction", check_drag_pan)

        def check_box_select():
            axis = current_axis()
            clear_crosshair()
            before = tuple(axis.get_xlim())
            mid_y = sum(axis.get_ylim()) / 2
            x0 = before[0] + (before[1] - before[0]) * 0.30
            x1 = before[0] + (before[1] - before[0]) * 0.60
            px0, py = axis.transData.transform((x0, mid_y))
            px1, _ = axis.transData.transform((x1, mid_y))
            window.canvas.callbacks.process(
                "button_press_event", MouseEvent("button_press_event", window.canvas, px0, py, button=3))
            window.canvas.callbacks.process(
                "motion_notify_event", MouseEvent("motion_notify_event", window.canvas, px1, py, button=3))
            window.canvas.callbacks.process(
                "button_release_event", MouseEvent("button_release_event", window.canvas, px1, py, button=3))
            app.processEvents()
            after = tuple(axis.get_xlim())
            assert (after[1] - after[0]) < (before[1] - before[0]) * 0.6, (
                f"right-drag box select did not narrow xlim: {before} -> {after}")
            interaction_state["box_xlim"] = after
            return {"before": before, "after": after}

        run("right_drag_box_zoom", "interaction", check_box_select)

        def check_double_click_restore():
            axis = current_axis()
            clear_crosshair()
            before = tuple(axis.get_xlim())
            mid = ((before[0] + before[1]) / 2, sum(axis.get_ylim()) / 2)
            px, py = axis.transData.transform(mid)
            window.canvas.callbacks.process(
                "button_press_event", MouseEvent("button_press_event", window.canvas, px, py,
                                                 button=1, dblclick=True))
            window.canvas.callbacks.process(
                "button_release_event", MouseEvent("button_release_event", window.canvas, px, py, button=1))
            app.processEvents()
            after = tuple(axis.get_xlim())
            initial = interaction_state.get("initial_xlim", (0.0, 1.0))
            assert (after[1] - after[0]) > (before[1] - before[0]) * 1.5, (
                f"double-click did not restore a wider view: {before} -> {after}")
            assert (after[1] - after[0]) >= (initial[1] - initial[0]) * 0.9, (
                f"double-click restored only {after}, initial full view was {initial}")
            return {"before": before, "after": after, "initial": initial}

        run("double_click_restore", "interaction", check_double_click_restore)

        def check_crosshair():
            axis = current_axis()
            before_lines = len(axis.lines)
            mid = ((axis.get_xlim()[0] + axis.get_xlim()[1]) / 2, sum(axis.get_ylim()) / 2)
            px, py = axis.transData.transform(mid)
            window.canvas.callbacks.process(
                "motion_notify_event", MouseEvent("motion_notify_event", window.canvas, px, py))
            app.processEvents()
            assert getattr(window, "_cross_vline", None) is not None, "vertical crosshair not created"
            assert getattr(window, "_cross_hline", None) is not None, "horizontal crosshair not created"
            assert len(axis.lines) >= before_lines + 2, "crosshair lines not added to the axes"
            text = getattr(window, "_cross_text", None)
            assert text is not None and text.get_text().strip(), "crosshair time label missing"
            return {"lines_before": before_lines, "lines_after": len(axis.lines),
                    "label": text.get_text().strip()}

        run("crosshair", "interaction", check_crosshair)

        def check_toggles():
            entries = []
            for attribute in ("plot_kline_cb", "plot_bi_cb", "plot_seg_cb",
                              "plot_zs_cb", "plot_bsp_cb", "plot_macd_cb"):
                clear_messages()
                box = getattr(window, attribute)
                old = box.isChecked()
                old_figure = window.canvas.figure
                box.setChecked(not old)
                window.refresh_btn.click()
                app.processEvents()
                assert not criticals, f"{attribute} toggle raised: {criticals}"
                assert window.canvas.figure is not old_figure, f"{attribute} toggle did not redraw the figure"
                axes_on = len(window.canvas.figure.axes)
                box.setChecked(old)
                window.refresh_btn.click()
                app.processEvents()
                assert not criticals, f"{attribute} restore raised: {criticals}"
                entries.append({"attribute": attribute, "toggled_to": not old, "axes": axes_on})
            return {"toggles": entries}

        run("display_toggles_redraw", "interaction", check_toggles)

        def check_screenshot():
            path = output.with_suffix(".png")
            window.canvas.figure.savefig(path, dpi=100)
            assert path.is_file() and path.stat().st_size > 0, f"screenshot not written: {path}"
            return {"path": str(path), "bytes": path.stat().st_size}

        run("screenshot", "interaction", check_screenshot)

        # ------------------------------------------------------------ 9. optional network
        if args.network:
            def check_network():
                clear_messages()
                result = {"attempted": True}

                def on_finished(chan):
                    result["chan"] = chan
                    window.on_analysis_finished(chan)

                def on_error(message):
                    result["error"] = message
                    window.on_analysis_error(message)

                thread = gui.SingleAnalysisThread("600000", window.get_chan_config(),
                                                  period_text="日线", days=30)
                thread.finished.connect(on_finished)
                thread.error.connect(on_error)
                thread.start()
                deadline = time.monotonic() + 180
                while thread.isRunning() and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.02)
                thread.wait(5000)
                app.processEvents()
                if thread.isRunning():
                    raise TimeoutError("network analysis thread did not finish within 180s")
                if "chan" in result:
                    assert window.chan is not None, "finished signal did not set window.chan"
                    assert window.canvas.figure.axes, "no axes drawn for network analysis"
                    assert window.analyze_btn.isEnabled(), "analyze button not re-enabled"
                    message = window.statusBar.currentMessage() if not callable(window.statusBar) else ""
                    assert "分析完成" in message, f"success feedback missing in status bar: {message!r}"
                    return {"outcome": "success", "code": result["chan"].code,
                            "klines": len(list(result["chan"][0].klu_iter())),
                            "status_message": message}
                message = result.get("error", "")
                assert message, "error signal carried no message"
                assert window.analyze_btn.isEnabled(), "analyze button not re-enabled after error"
                assert criticals, "failure feedback QMessageBox.critical not shown"
                return {"outcome": "service_or_source_error", "error": message,
                        "dialog": criticals[-1], "note": "network/service failure vs source error not distinguished"}

            run("network_single_stock_daily", "network", check_network)

    try:
        window.close()
        app.processEvents()
    except Exception:
        pass

    finalize(report, checks, started, output)

    failed = [check["name"] for check in checks if check["status"] != "PASS"]
    if failed:
        print(f"FAIL: {len(failed)} check(s) failed: {failed}", flush=True)
        return 1
    print(f"PASS: {len(checks)} GUI checks; report: {output}", flush=True)
    return 0


def finalize(report, checks, started, output):
    passed = sum(1 for check in checks if check["status"] == "PASS")
    failed = [check for check in checks if check["status"] != "PASS"]
    report["finished_at"] = datetime.now().isoformat(timespec="seconds")
    report["duration_s"] = round(time.time() - started, 1)
    report["summary"] = {"total": len(checks), "passed": passed, "failed": len(failed),
                         "failed_checks": [check["name"] for check in failed]}
    report["status"] = "PASS" if checks and not failed else "FAIL"
    output.write_text(json.dumps(json_safe(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report: {output} ({report['status']}, {passed}/{len(checks)} passed, "
          f"{report['duration_s']}s)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
