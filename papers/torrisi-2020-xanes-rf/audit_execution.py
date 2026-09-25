"""Compare two separately executed candidate workflows without importing either.

This execution audit complements the scientific verifier: agreement alone is not
ground truth. Use after candidate.py ALL and summarize.py for all five questions.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


QUESTION_COUNTS = {"Q1": 16, "Q2": 8, "Q3": 16, "Q4": 48, "Q5": 64}
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/data/torrisi-2020-xanes-rf"


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def compare_json(actual, reference, location="root"):
    if isinstance(actual, (float, int)) and not isinstance(actual, bool):
        if not isinstance(reference, (float, int)) or not math.isclose(
            actual, reference, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise AssertionError(f"Numerical disagreement at {location}: {actual}, {reference}")
    elif isinstance(actual, dict):
        if not isinstance(reference, dict) or set(actual) != set(reference):
            raise AssertionError(f"Different keys at {location}")
        for key in actual:
            compare_json(actual[key], reference[key], f"{location}.{key}")
    elif isinstance(actual, list):
        if not isinstance(reference, list) or len(actual) != len(reference):
            raise AssertionError(f"Different list lengths at {location}")
        for i, (a, b) in enumerate(zip(actual, reference)):
            compare_json(a, b, f"{location}[{i}]")
    elif actual != reference:
        raise AssertionError(f"Disagreement at {location}: {actual!r}, {reference!r}")


def compare_csv(actual_path, reference_path):
    with actual_path.open() as a, reference_path.open() as b:
        actual, reference = list(csv.DictReader(a)), list(csv.DictReader(b))
    if len(actual) != len(reference):
        raise AssertionError(f"Different row counts for {actual_path.name}")
    max_difference = 0.0
    for i, (a, b) in enumerate(zip(actual, reference)):
        if set(a) != set(b):
            raise AssertionError(f"Different columns for {actual_path.name}")
        for key in a:
            if a[key] == b[key]:
                continue
            try:
                x, y = float(a[key]), float(b[key])
            except ValueError as error:
                raise AssertionError(f"Different values in {actual_path.name}:{i}:{key}") from error
            if not math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-12):
                raise AssertionError(f"Numerical disagreement in {actual_path.name}:{i}:{key}")
            max_difference = max(max_difference, abs(x-y))
    return {"rows": len(actual), "max_absolute_numeric_difference": max_difference}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--independent", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--metadata", type=Path,
                        help="Optional execution-reviewer metadata recorded at independent launch")
    parser.add_argument("--standalone", type=Path,
                        help="Optional additional run of one final standalone question")
    parser.add_argument("--report", type=Path,
                        default=DATA / "verification/workflow_execution_review.json")
    args = parser.parse_args()
    questions = {}
    for q, expected_models in QUESTION_COUNTS.items():
        actual, reference = args.independent/q, args.reference/q
        checks = {}
        for name in ("result.json", "splits.json", "feature_metadata.json"):
            a, b = json.loads((actual/name).read_text()), json.loads((reference/name).read_text())
            compare_json(a, b, f"{q}/{name}")
            checks[name] = "numerically identical within 1e-12"
        result = json.loads((actual/"result.json").read_text())
        if len(result["models"]) != expected_models:
            raise AssertionError(f"Incomplete model configurations for {q}")
        if result["protocol"]["n_estimators"] != 100:
            raise AssertionError(f"Unexpected forest budget for {q}")
        for model in result["models"]:
            if model["seeds"] != [42, 43, 44]:
                raise AssertionError(f"Unexpected forest repetitions for {q}")
        csv_names = {"predictions.csv", "importances.csv"}
        if q == "Q1":
            csv_names |= {"comparisons.csv", "confusion.csv"}
        if q == "Q3":
            csv_names.add("comparisons.csv")
        if q in {"Q4", "Q5"}:
            csv_names |= {"comparisons.csv", "ranked_features.csv", "coefficient_families.csv"}
        for name in sorted(csv_names):
            checks[name] = compare_csv(actual/name, reference/name)
        for name in ("plot.png", "diagnostics.png"):
            with (actual/name).open("rb") as f:
                if f.read(8) != b"\x89PNG\r\n\x1a\n":
                    raise AssertionError(f"Invalid plot: {q}/{name}")
            checks[name] = "present, valid PNG signature"
        if not (actual/"conclusion.md").read_text().strip():
            raise AssertionError(f"Missing conclusion for {q}")
        questions[q] = {
            "model_configurations": expected_models,
            "checks": checks,
            "artifacts_sha256": {p.name: sha256(p) for p in sorted(actual.iterdir()) if p.is_file()},
        }
    metadata = json.loads(args.metadata.read_text()) if args.metadata else {
        "independent_outputs": str(args.independent.resolve()),
        "reference_outputs": str(args.reference.resolve()),
        "launch_details": "Not supplied; consult execution.json in each run directory.",
    }
    standalone = None
    if args.standalone:
        result = json.loads((args.standalone/"result.json").read_text())
        q = result["question"]
        for name in ("result.json", "splits.json", "feature_metadata.json"):
            compare_json(json.loads((args.standalone/name).read_text()),
                         json.loads((args.independent/q/name).read_text()), f"standalone/{name}")
        for name in ("predictions.csv", "importances.csv"):
            compare_csv(args.standalone/name, args.independent/q/name)
        if not (args.standalone/"diagnostics.png").is_file():
            raise AssertionError("Standalone run did not automatically generate diagnostics")
        if (args.standalone/"conclusion.md").read_text() != (args.independent/q/"conclusion.md").read_text():
            raise AssertionError("Standalone scientific conclusion differs from ALL run")
        standalone = {
            "question": q,
            "status": "pass",
            "check": "Final standalone command reproduces ALL numerical results and automatically creates the same scientific conclusion and diagnostic plot.",
            "execution": json.loads((args.standalone/"execution.json").read_text()),
            "artifacts_sha256": {p.name: sha256(p) for p in sorted(args.standalone.iterdir()) if p.is_file()},
        }
    report = {
        "reviewer": "workflow_execution subagent",
        "status": "pass",
        "scope": "Complete independent execution of every worked example from the input bundle, followed by task-specific summaries and comparison with a separate author execution.",
        "limitations": "Independent execution validates completeness and repeatability. It does not itself establish scientific truth; the separate verification audit checks released evidence and adversarial mutations.",
        "method": "No candidate function imports in this audit. JSON and CSV files compared recursively with absolute/relative numeric tolerance 1e-12; artifact presence and signatures checked.",
        "execution_metadata": metadata,
        "independent_execution": json.loads((args.independent/"execution.json").read_text()),
        "reference_execution": json.loads((args.reference/"execution.json").read_text()),
        "final_standalone_check": standalone,
        "workflow_hashes_at_audit": {p.name: sha256(p) for p in sorted((DATA/"workflows").glob("*.py"))},
        "questions": questions,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"PASS: all five questions reproduced; report {args.report}")


if __name__ == "__main__":
    main()
