#!/usr/bin/env python3
"""Independent evaluator-side replay from freshly exported solver-only inputs."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "papers/chen-2021-l-edge"
BASE = ROOT / "docs/data/chen-2021-l-edge"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return bool(np.isclose(a, b, rtol=1e-10, atol=1e-12, equal_nan=True))
    if isinstance(a, str) and isinstance(b, str):
        try:
            return equal(float(a), float(b))
        except ValueError:
            pass
    return a == b


def compare(a, b):
    if not b.is_file():
        return {"present": False, "pass": False}
    result = {"present": True, "sha256": sha(a), "reference_sha256": sha(b)}
    result["byte_identical"] = result["sha256"] == result["reference_sha256"]
    if a.suffix == ".npz":
        with np.load(a) as x, np.load(b) as y:
            result["arrays"] = len(x.files)
            result["pass"] = set(x.files) == set(y.files) and all(
                x[k].shape == y[k].shape and np.allclose(x[k], y[k], rtol=1e-10, atol=1e-12, equal_nan=True)
                for k in x.files
            )
    elif a.suffix == ".json":
        result["pass"] = equal(json.loads(a.read_text()), json.loads(b.read_text()))
    elif a.suffix == ".csv":
        with a.open() as fa, b.open() as fb:
            x, y = list(csv.DictReader(fa)), list(csv.DictReader(fb))
        result["rows"] = len(x)
        result["pass"] = equal(x, y)
    else:
        result["pass"] = result["byte_identical"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    commands = []
    for q in ("Q1", "Q2", "Q3"):
        command = [sys.executable, str(PAPER / "export_agent_bundle.py"), q,
                   "--output", str(args.work / "bundles" / q)]
        subprocess.run(command, check=True)
        commands.append(command)
    hashes = {}
    for q in ("Q1", "Q2", "Q3"):
        bundle = args.work / "bundles" / q
        hashes[q] = {str(p.relative_to(bundle)): sha(p) for p in sorted(bundle.rglob("*")) if p.is_file()}
    assert all(hashes[q]["inputs/" + p.name] == sha(p)
               for q in hashes for p in (BASE / "inputs").glob("*.gz"))
    candidate = BASE / "workflows/candidate.py"
    command = [sys.executable, str(candidate), "all", "--inputs",
               str(args.work / "bundles/Q1/inputs"), "--output", str(args.work / "outputs")]
    commands.append(command)
    initial_hash = sha(candidate)
    started = time.time()
    with (args.work / "execution.log").open("w") as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, "MPLCONFIGDIR": str(args.work / "mpl")})
    elapsed = time.time() - started
    checks = {}
    if completed.returncode == 0:
        for p in sorted((args.work / "outputs").rglob("*")):
            if p.is_file():
                key = str(p.relative_to(args.work / "outputs"))
                checks[key] = compare(p, args.reference / key)
    record = {
        "reviewer_role": "Independent adversarial question reviewer performing fresh execution replay",
        "commands": commands, "exit_code": completed.returncode, "elapsed_seconds": elapsed,
        "candidate_sha256": initial_hash, "candidate_unchanged_during_run": sha(candidate) == initial_hash,
        "python": sys.version, "platform": platform.platform(),
        "dependencies": {p: importlib.metadata.version(p) for p in
                         ("numpy", "scipy", "scikit-learn", "pymatgen", "spglib", "matplotlib")},
        "exported_file_hashes": hashes, "input_boundary": "task.json plus eight unchanged native gzip inputs per task",
        "reference_directory": str(args.reference.resolve()), "output_directory": str((args.work / "outputs").resolve()),
        "log": str((args.work / "execution.log").resolve()),
        "comparison_policy": "JSON/CSV numbers and NPZ arrays rtol=1e-10, atol=1e-12; remaining files byte equality. No metrics imported from the reference during execution.",
        "comparisons": checks,
        "execution_and_reproducibility_pass": completed.returncode == 0 and sha(candidate) == initial_hash
            and bool(checks) and all(r["pass"] for r in checks.values()),
    }
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"record": str(args.record), "pass": record["execution_and_reproducibility_pass"],
                      "elapsed_seconds": elapsed, "compared_files": len(checks)}))
    raise SystemExit(0 if record["execution_and_reproducibility_pass"] else 1)


if __name__ == "__main__":
    main()
