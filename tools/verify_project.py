"""Run the four known offline regressions, verify baseline bytes, optionally compare full analyses."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
REGRESSIONS = ("test_cross_year_infer.py", "test_cross_year_e2e.py", "test_user_2026_01.py", "test_with_year_filter.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="Verified snapshot source tree; also compares the three private sample files")
    parser.add_argument("--razor-changes", type=Path,
                        help="Allow original-file changes listed in this JSON manifest (schema: "
                             '{"modified": {path: {old_sha256, new_sha256, reason}}, "deleted": {path: reason}, '
                             '"added": [path]}); default behavior rejects every original-file change')
    parser.add_argument("--output", type=Path, default=ROOT / ".local-validation" / "verification.json")
    args = parser.parse_args()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    report = {"python": sys.version, "checks": []}
    baseline = json.loads((ROOT / "docs" / "source-baseline-sha256.json").read_text(encoding="utf-8"))
    if args.razor_changes:
        import razor_acceptance
        manifest_path = args.razor_changes if args.razor_changes.is_absolute() else ROOT / args.razor_changes
        if not manifest_path.is_file():
            raise RuntimeError(f"Change manifest missing: {manifest_path} (schema: {razor_acceptance.MANIFEST_SCHEMA})")
        problems = []
        manifest = razor_acceptance.validate_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")), problems)
        if problems:
            raise RuntimeError(f"Change manifest invalid: {problems}; schema: {razor_acceptance.MANIFEST_SCHEMA}")
        enforced = razor_acceptance.enforce_baseline_bytes(baseline, manifest)
        if enforced["problems"]:
            raise RuntimeError("Original source changed without a manifest allowance: "
                               + json.dumps(enforced["problems"], ensure_ascii=False))
        report["checks"].append({"name": "original_python_bytes", "files": len(baseline), "status": "PASS",
                                 "manifest": str(manifest_path),
                                 "modified": enforced["allowed_modified"],
                                 "deleted": [item["path"] for item in enforced["allowed_deleted"]]})
    else:
        for name, expected in baseline.items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Original source changed: {name}")
        report["checks"].append({"name": "original_python_bytes", "files": len(baseline), "status": "PASS"})
    count = 0
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", ".local-backups", ".local-validation", "build", "dist", "__pycache__"} for part in path.relative_to(ROOT).parts):
            continue
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        count += 1
    report["checks"].append({"name": "python_syntax", "files": count, "status": "PASS"})
    for name in REGRESSIONS:
        result = subprocess.run([sys.executable, "-B", str(ROOT / "Debug" / name)], cwd=ROOT,
                                env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
        print(result.stdout, end="")
        if result.returncode:
            raise RuntimeError(f"{name} failed:\n{result.stderr}")
        report["checks"].append({"name": name, "status": "PASS"})
    if args.reference:
        results = []
        for label, source in (("reference", args.reference.resolve()), ("development", ROOT)):
            output = ROOT / ".local-validation" / f"{label}-fingerprint.json"
            subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "analysis_fingerprint.py"),
                            "--source", str(source), "--output", str(output)], cwd=source, env=env, check=True, timeout=180)
            results.append(json.loads(output.read_text(encoding="utf-8")))
        if results[0] != results[1]:
            raise RuntimeError("Reference and development analyses differ; inspect local fingerprint JSON files")
        report["checks"].append({"name": "sample_analysis_equivalence", "cases": len(results[0]), "status": "PASS"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(report['checks'])} checks; report: {args.output}")


if __name__ == "__main__":
    main()
