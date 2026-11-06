r"""Total acceptance for the Razor edit: baseline bytes + change manifest, syntax, regressions,
full analysis fingerprint comparison, optional GUI checks and optional reference-tree equivalence.

Every check is reported as PASS/FAIL with details in a JSON report; the exit code is 0 only when
all checks pass. Nothing is silently skipped: a modified or missing original file that is not
covered by docs/razor-source-changes.json fails acceptance explicitly, and a missing manifest is
an explicit error.

Change manifest schema (docs/razor-source-changes.json):
{
  "modified": {"<workspace-relative path>": {"old_sha256": "<64 hex>",
                                             "new_sha256": "<64 hex>",
                                             "reason": "<why the original file changed>"}},
  "deleted":  {"<workspace-relative path>": "<why the original file was removed>"},
  "added":    ["<workspace-relative path>", ...]
}

Run:
  .\.venv\Scripts\python.exe -B tools\razor_acceptance.py
  .\.venv\Scripts\python.exe -B tools\razor_acceptance.py --gui
  .\.venv\Scripts\python.exe -B tools\razor_acceptance.py --reference C:\path\to\verified\snapshot
"""
import argparse
import ast
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "source-baseline-sha256.json"
DEFAULT_MANIFEST = ROOT / "docs" / "razor-source-changes.json"
DEFAULT_COMPARE = ROOT / ".local-validation" / "razor" / "analysis-before.json"
DEFAULT_FINGERPRINT_OUTPUT = ROOT / ".local-validation" / "razor" / "analysis-after.json"
DEFAULT_GUI_REPORT = ROOT / ".local-validation" / "razor" / "gui-after.json"
DEFAULT_OUTPUT = ROOT / ".local-validation" / "razor" / "acceptance.json"
REGRESSIONS = ("test_cross_year_infer.py", "test_cross_year_e2e.py",
               "test_user_2026_01.py", "test_with_year_filter.py")
EXCLUDED_PARTS = {".git", ".venv", ".local-backups", ".local-validation", "build", "dist", "__pycache__"}
ELEMENTS = ("raw_kline", "combined_kline", "bi", "seg", "zs", "segzs", "bsp", "seg_bsp")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_SCHEMA = ('{"modified": {"path": {"old_sha256": "64-hex", "new_sha256": "64-hex", '
                   '"reason": "non-empty"}}, "deleted": {"path": "reason"}, "added": ["path"]}')


class CheckFailure(Exception):
    """A check failed with structured detail."""

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


def json_safe(value):
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


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def posix(path):
    return Path(path).as_posix()


def resolve_against_root(path_arg):
    path = Path(path_arg)
    return path if path.is_absolute() else (ROOT / path)


def decode_output(raw):
    if not raw:
        return ""
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def run_process(command, *, cwd=None, timeout=600):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    completed = subprocess.run(command, cwd=str(cwd or ROOT), env=env, capture_output=True,
                               timeout=timeout)
    return subprocess.CompletedProcess(completed.args, completed.returncode,
                                       decode_output(completed.stdout),
                                       decode_output(completed.stderr))


def tail(text, limit=1200):
    text = (text or "").strip()
    return text[-limit:]


def git(*args):
    try:
        result = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                                encoding="utf-8", timeout=60)
        return result
    except Exception:  # noqa: BLE001 - git is optional evidence, never crash acceptance on it
        return None


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_baseline(baseline, problems):
    if not isinstance(baseline, dict):
        problems.append(f"baseline is {type(baseline).__name__}, expected an object of path -> sha256")
        return
    if len(baseline) != 96:
        problems.append(f"baseline lists {len(baseline)} files, expected 96 original files")
    for name, digest in baseline.items():
        if not isinstance(name, str) or not name.strip():
            problems.append(f"baseline has an invalid path key: {name!r}")
        if not isinstance(digest, str) or not SHA_RE.match(digest):
            problems.append(f"baseline has an invalid sha256 for {name!r}: {digest!r}")


def validate_manifest(manifest, problems):
    """Validate the change-manifest schema strictly; returns normalized manifest."""
    if not isinstance(manifest, dict):
        problems.append(f"manifest is {type(manifest).__name__}, expected an object")
        return {"modified": {}, "deleted": {}, "added": []}
    known = {"modified", "deleted", "added"}
    unknown = sorted(set(manifest) - known)
    if unknown:
        problems.append(f"manifest has unknown top-level keys: {unknown}")
    if not (set(manifest) & known):
        problems.append("manifest has none of the keys 'modified', 'deleted', 'added'")
    normalized = {"modified": {}, "deleted": {}, "added": []}

    def valid_relative(path):
        if not isinstance(path, str) or not path.strip():
            return False
        candidate = Path(path)
        return not candidate.is_absolute() and ".." not in candidate.parts

    modified = manifest.get("modified", {})
    if not isinstance(modified, dict):
        problems.append("manifest 'modified' must be an object of path -> {old_sha256,new_sha256,reason}")
        modified = {}
    for name, entry in modified.items():
        if not valid_relative(name):
            problems.append(f"modified path is not workspace-relative: {name!r}")
            continue
        if not isinstance(entry, dict):
            problems.append(f"modified[{name!r}] must be an object with old_sha256/new_sha256/reason")
            continue
        old = entry.get("old_sha256")
        new = entry.get("new_sha256")
        reason = entry.get("reason")
        if not isinstance(old, str) or not SHA_RE.match(old):
            problems.append(f"modified[{name!r}].old_sha256 is not a 64-hex sha256: {old!r}")
        if not isinstance(new, str) or not SHA_RE.match(new):
            problems.append(f"modified[{name!r}].new_sha256 is not a 64-hex sha256: {new!r}")
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"modified[{name!r}].reason must be a non-empty string")
        if isinstance(old, str) and isinstance(new, str) and old == new:
            problems.append(f"modified[{name!r}] has identical old/new sha256")
        normalized["modified"][posix(name)] = entry

    deleted = manifest.get("deleted", {})
    if not isinstance(deleted, dict):
        problems.append("manifest 'deleted' must be an object of path -> reason")
        deleted = {}
    for name, reason in deleted.items():
        if not valid_relative(name):
            problems.append(f"deleted path is not workspace-relative: {name!r}")
            continue
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"deleted[{name!r}] reason must be a non-empty string")
        normalized["deleted"][posix(name)] = reason

    added = manifest.get("added", [])
    if not isinstance(added, list):
        problems.append("manifest 'added' must be a list of workspace-relative paths")
        added = []
    seen = set()
    for name in added:
        if not valid_relative(name):
            problems.append(f"added entry is not workspace-relative: {name!r}")
            continue
        if name in seen:
            problems.append(f"added entry is duplicated: {name!r}")
            continue
        seen.add(name)
        normalized["added"].append(posix(name))
    return normalized


def enforce_baseline_bytes(baseline, manifest, root=ROOT):
    """Match every original baseline file against its bytes and the allowed-change manifest."""
    unchanged, allowed_modified, allowed_deleted, problems = [], [], [], []
    for name, expected in sorted(baseline.items()):
        target = Path(root) / name
        if not target.is_file():
            if name in manifest["deleted"]:
                allowed_deleted.append({"path": name, "reason": manifest["deleted"][name]})
            else:
                problems.append({"path": name, "problem": "original file is missing and not "
                                                          "allowed by manifest.deleted"})
            continue
        actual = sha256_file(target)
        if actual == expected:
            if name in manifest["modified"]:
                problems.append({"path": name, "problem": "manifest.modified lists this file "
                                                          "but its bytes still match the baseline"})
            else:
                unchanged.append(name)
            continue
        entry = manifest["modified"].get(name)
        if entry is None:
            problems.append({"path": name, "problem": "original file changed and is not allowed "
                                                      "by manifest.modified",
                             "old_sha256": expected, "new_sha256": actual})
            continue
        if entry.get("old_sha256") != expected:
            problems.append({"path": name, "problem": "manifest.modified old_sha256 does not match "
                                                      "the baseline value",
                             "baseline": expected, "manifest_old": entry.get("old_sha256")})
        if entry.get("new_sha256") != actual:
            problems.append({"path": name, "problem": "manifest.modified new_sha256 does not match "
                                                      "the current file",
                             "current": actual, "manifest_new": entry.get("new_sha256")})
        if not entry.get("reason", "").strip():
            problems.append({"path": name, "problem": "manifest.modified reason is empty"})
        if not any(item.get("path") == name for item in problems):
            allowed_modified.append(name)
    for name in sorted(manifest["modified"]):
        if name not in baseline:
            problems.append({"path": name, "problem": "manifest.modified lists a path that is not "
                                                      "an original baseline file"})
    for name in sorted(manifest["deleted"]):
        if name not in baseline:
            problems.append({"path": name, "problem": "manifest.deleted lists a path that is not "
                                                      "an original baseline file"})
        elif (Path(root) / name).exists():
            problems.append({"path": name, "problem": "manifest.deleted lists a file that still exists"})
    for name in manifest["added"]:
        if name in baseline:
            problems.append({"path": name, "problem": "manifest.added lists an original baseline file"})
        elif not (Path(root) / name).is_file():
            problems.append({"path": name, "problem": "manifest.added file does not exist"})
    return {"unchanged": unchanged, "allowed_modified": allowed_modified,
            "allowed_deleted": allowed_deleted, "problems": problems}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--changes", type=Path, default=DEFAULT_MANIFEST,
                        help="allowed-change manifest (default: docs/razor-source-changes.json)")
    parser.add_argument("--compare", type=Path, default=DEFAULT_COMPARE,
                        help="pre-Razor analysis fingerprint to compare against "
                             "(default: .local-validation/razor/analysis-before.json)")
    parser.add_argument("--fingerprint-output", type=Path, default=DEFAULT_FINGERPRINT_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gui", action="store_true", help="also run tools/razor_gui_check.py and require all PASS")
    parser.add_argument("--gui-report", type=Path, default=DEFAULT_GUI_REPORT)
    parser.add_argument("--reference", type=Path,
                        help="verified snapshot tree; also compares its analysis fingerprints with this tree")
    parser.add_argument("--timeout", type=float, default=900.0, help="per subprocess timeout in seconds")
    args = parser.parse_args()

    started = time.time()
    started_at = datetime.now().isoformat(timespec="seconds")
    output = resolve_against_root(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("MPLCONFIGDIR", str(output.parent / "mpl-cache"))

    report = {
        "tool": "tools/razor_acceptance.py",
        "started_at": started_at,
        "python": sys.version,
        "root": str(ROOT),
        "manifest": str(resolve_against_root(args.changes)),
        "compare": str(resolve_against_root(args.compare)),
        "gui": args.gui,
        "reference": str(resolve_against_root(args.reference)) if args.reference else None,
        "checks": [],
    }
    checks = report["checks"]

    head = git("rev-parse", "HEAD")
    report["git_head"] = head.stdout.strip() if head is not None and head.returncode == 0 else None

    def record(name, group, status, detail=None):
        checks.append({"group": group, "name": name, "status": status, "detail": json_safe(detail)})
        line = f"{status} [{group}] {name}"
        if status != "PASS" and detail:
            line += f" :: {json.dumps(json_safe(detail), ensure_ascii=False)[:600]}"
        print(line, flush=True)

    def run(name, group, fn):
        try:
            detail = fn()
        except CheckFailure as exc:
            record(name, group, "FAIL", exc.detail if exc.detail is not None else str(exc))
            return False
        except Exception as exc:  # noqa: BLE001 - every check must be recorded
            record(name, group, "FAIL", f"{type(exc).__name__}: {exc}")
            return False
        record(name, group, "PASS", detail)
        return True

    # ---------------------------------------------------------------- 1. baseline json + manifest
    baseline = {}
    baseline_problems = []

    def check_baseline_json():
        if not BASELINE.is_file():
            raise CheckFailure(f"baseline file missing: {BASELINE}")
        raw = BASELINE.read_bytes()
        try:
            loaded = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise CheckFailure(f"baseline file is not valid JSON: {type(exc).__name__}: {exc}")
        problems = []
        validate_baseline(loaded, problems)
        if problems:
            raise CheckFailure("baseline structure is invalid", {"problems": problems})
        baseline.update(loaded)
        integrity = {"file": str(BASELINE), "sha256": sha256_bytes(raw), "files": len(loaded)}
        rel = posix(BASELINE.relative_to(ROOT))
        tracked = git("ls-files", "--error-unmatch", rel)
        if tracked is None:
            integrity["git"] = "git unavailable; baseline file self-integrity not verified"
        elif tracked.returncode != 0:
            raise CheckFailure(f"baseline file is not tracked by git: {rel}")
        else:
            head_file = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(ROOT),
                                       capture_output=True, timeout=60)
            if head_file.returncode == 0 and head_file.stdout != raw:
                raise CheckFailure(
                    f"baseline file {rel} differs from git HEAD; the original-file baseline may have "
                    "been edited to hide changes")
            integrity["git"] = "unchanged vs HEAD"
        return integrity

    run("baseline_json_integrity", "baseline", check_baseline_json)

    def check_manifest_and_bytes():
        manifest_path = resolve_against_root(args.changes).resolve()
        if not manifest_path.is_file():
            raise CheckFailure(
                f"change manifest missing: {manifest_path}; create it (schema: {MANIFEST_SCHEMA}) "
                "so every modified/deleted original file is explicitly allowed")
        raw = manifest_path.read_bytes()
        try:
            loaded = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise CheckFailure(f"change manifest is not valid JSON: {type(exc).__name__}: {exc}; "
                               f"schema: {MANIFEST_SCHEMA}")
        problems = []
        manifest = validate_manifest(loaded, problems)
        if problems:
            raise CheckFailure(f"change manifest schema is invalid; schema: {MANIFEST_SCHEMA}",
                               {"problems": problems})
        if not baseline:
            raise CheckFailure("baseline json could not be loaded; cannot enforce original-file bytes")
        enforced = enforce_baseline_bytes(baseline, manifest)
        unauthorized = enforced["problems"]
        detail = {"manifest_sha256": sha256_bytes(raw),
                  "baseline_files": len(baseline),
                  "unchanged": len(enforced["unchanged"]),
                  "allowed_modified": enforced["allowed_modified"],
                  "allowed_deleted": enforced["allowed_deleted"],
                  "added": manifest["added"]}
        if unauthorized:
            detail["problems"] = unauthorized
            raise CheckFailure(f"{len(unauthorized)} baseline file(s) are not covered by the change manifest",
                               detail)
        return detail

    run("baseline_bytes_vs_manifest", "baseline", check_manifest_and_bytes)

    # ---------------------------------------------------------------- 2. python syntax
    def check_syntax():
        errors, count = [], 0
        for path in sorted(ROOT.rglob("*.py")):
            if any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
                continue
            count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            except SyntaxError as exc:
                errors.append({"file": posix(path.relative_to(ROOT)), "line": exc.lineno,
                               "message": str(exc)})
        if errors:
            raise CheckFailure(f"{len(errors)} python file(s) have syntax errors", {"errors": errors})
        return {"files": count}

    run("python_syntax", "syntax", check_syntax)

    # ---------------------------------------------------------------- 3. four offline regressions
    for regression in REGRESSIONS:
        def check_regression(regression=regression):
            script = ROOT / "Debug" / regression
            if not script.is_file():
                raise CheckFailure(f"regression script missing: {script}")
            result = run_process([sys.executable, "-B", str(script)], timeout=120)
            detail = {"script": f"Debug/{regression}", "returncode": result.returncode,
                      "stdout_tail": tail(result.stdout, 800), "stderr_tail": tail(result.stderr, 800)}
            if result.returncode != 0:
                raise CheckFailure(f"{regression} exited with {result.returncode}", detail)
            return detail
        run(f"regression_{regression[:-3]}", "regressions", check_regression)

    # ---------------------------------------------------------------- 4. analysis fingerprint comparison
    def check_analysis():
        compare_path = resolve_against_root(args.compare).resolve()
        if not compare_path.is_file():
            raise CheckFailure(f"pre-Razor analysis fingerprint missing: {compare_path}; pass --compare PATH")
        before = load_json(compare_path)
        fingerprint_script = ROOT / "tools" / "analysis_fingerprint.py"
        after_path = resolve_against_root(args.fingerprint_output).resolve()
        after_path.parent.mkdir(parents=True, exist_ok=True)
        result = run_process([sys.executable, "-B", str(fingerprint_script), "--source", str(ROOT),
                              "--output", str(after_path)], timeout=args.timeout)
        if result.returncode != 0:
            raise CheckFailure(f"analysis_fingerprint.py failed with {result.returncode}",
                               {"stdout_tail": tail(result.stdout), "stderr_tail": tail(result.stderr)})
        after = load_json(after_path)
        before_sha = sha256_file(compare_path)
        detail = {"before": str(compare_path), "before_sha256": before_sha,
                  "after": str(after_path), "after_sha256": sha256_file(after_path)}
        diffs = []
        if not isinstance(before, list) or not isinstance(after, list):
            raise CheckFailure("fingerprint files must be JSON lists", detail)
        if len(before) != len(after):
            diffs.append({"field": "case_count", "expected": len(before), "actual": len(after)})
        before_map = {(item.get("sample"), item.get("bi_strict")): item for item in before}
        after_map = {(item.get("sample"), item.get("bi_strict")): item for item in after}
        if set(before_map) != set(after_map):
            diffs.append({"field": "cases", "expected": sorted(map(str, before_map)),
                          "actual": sorted(map(str, after_map))})
        compared_fields = 0
        for key in sorted(before_map, key=str):
            if key not in after_map:
                continue
            left, right = before_map[key], after_map[key]
            case = f"{key[0]}/bi_strict={key[1]}"
            for field in ("first_time", "last_time"):
                compared_fields += 1
                if left.get(field) != right.get(field):
                    diffs.append({"case": case, "field": field, "expected": left.get(field),
                                  "actual": right.get(field)})
            left_elements = left.get("elements", {})
            right_elements = right.get("elements", {})
            compared_fields += 1
            if set(left_elements) != set(right_elements):
                diffs.append({"case": case, "field": "element_keys",
                              "expected": sorted(left_elements), "actual": sorted(right_elements)})
            for element in ELEMENTS:
                if element not in left_elements or element not in right_elements:
                    continue
                for field in ("count", "sha256"):
                    compared_fields += 1
                    expected_value = left_elements[element].get(field)
                    actual_value = right_elements[element].get(field)
                    if expected_value != actual_value:
                        diffs.append({"case": case, "field": f"{element}.{field}",
                                      "expected": expected_value, "actual": actual_value})
        detail.update({"cases": len(before_map), "compared_fields": compared_fields,
                       "elements": list(ELEMENTS)})
        if diffs:
            detail["diffs"] = diffs
            raise CheckFailure(f"{len(diffs)} analysis fingerprint field(s) differ from the pre-Razor baseline",
                               detail)
        return detail

    run("analysis_fingerprint_compare", "analysis", check_analysis)

    # ---------------------------------------------------------------- 5. optional reference equivalence
    if args.reference:
        def check_reference():
            reference = resolve_against_root(args.reference).resolve()
            if not (reference / "A111.txt").is_file():
                raise CheckFailure(f"reference tree has no A111.txt: {reference}")
            fingerprint_script = ROOT / "tools" / "analysis_fingerprint.py"
            results = {}
            for label, source in (("reference", reference), ("development", ROOT)):
                target = output.parent / f"{label}-fingerprint.json"
                result = run_process([sys.executable, "-B", str(fingerprint_script),
                                      "--source", str(source), "--output", str(target)],
                                     cwd=source, timeout=args.timeout)
                if result.returncode != 0:
                    raise CheckFailure(f"analysis_fingerprint.py failed for {label} ({result.returncode})",
                                       {"stdout_tail": tail(result.stdout),
                                        "stderr_tail": tail(result.stderr)})
                results[label] = load_json(target)
            if results["reference"] != results["development"]:
                raise CheckFailure("reference and development analyses differ; inspect the two fingerprint files",
                                   {"reference": str(output.parent / "reference-fingerprint.json"),
                                    "development": str(output.parent / "development-fingerprint.json")})
            return {"cases": len(results["development"]), "reference": str(reference)}
        run("reference_fingerprint_equivalence", "reference", check_reference)

    # ---------------------------------------------------------------- 6. optional GUI check
    if args.gui:
        def check_gui():
            gui_script = ROOT / "tools" / "razor_gui_check.py"
            if not gui_script.is_file():
                raise CheckFailure(f"GUI check script missing: {gui_script}")
            gui_report_path = resolve_against_root(args.gui_report).resolve()
            gui_before = ROOT / ".local-validation" / "razor" / "gui-before.json"
            command = [sys.executable, "-B", str(gui_script), "--source", str(ROOT),
                       "--samples", str(ROOT), "--output", str(gui_report_path)]
            if gui_before.is_file():
                command += ["--gui-before", str(gui_before)]
            result = run_process(command, timeout=args.timeout)
            detail = {"report": str(gui_report_path), "returncode": result.returncode,
                      "stdout_tail": tail(result.stdout), "stderr_tail": tail(result.stderr)}
            if not gui_report_path.is_file():
                raise CheckFailure(f"GUI check did not write a report (exit {result.returncode})", detail)
            gui_report = load_json(gui_report_path)
            detail["gui_status"] = gui_report.get("status")
            detail["summary"] = gui_report.get("summary")
            if gui_report.get("status") != "PASS" or result.returncode != 0:
                failed = [check["name"] for check in gui_report.get("checks", [])
                          if check.get("status") != "PASS"]
                detail["failed_checks"] = failed
                raise CheckFailure(f"GUI checks failed: {failed or 'no report status'}", detail)
            return detail
        run("gui_checks", "gui", check_gui)

    # ---------------------------------------------------------------- report
    passed = [check for check in checks if check["status"] == "PASS"]
    failed = [check for check in checks if check["status"] != "PASS"]
    report["finished_at"] = datetime.now().isoformat(timespec="seconds")
    report["duration_s"] = round(time.time() - started, 1)
    report["summary"] = {"total": len(checks), "passed": len(passed), "failed": len(failed),
                         "failed_checks": [check["name"] for check in failed]}
    report["status"] = "PASS" if checks and not failed else "FAIL"
    output.write_text(json.dumps(json_safe(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failed:
        print(f"FAIL: {len(failed)}/{len(checks)} checks failed: "
              f"{[check['name'] for check in failed]}; report: {output}", flush=True)
        return 1
    print(f"PASS: all {len(checks)} acceptance checks; report: {output}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
