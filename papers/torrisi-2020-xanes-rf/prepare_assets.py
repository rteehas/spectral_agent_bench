"""Project the earliest spectra in the public release into answer-free inputs.

This author-side preparation requires the extracted MatriO release. It preserves
every source row and only removes fields; it does not clean or fit spectra.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "docs/data/torrisi-2020-xanes-rf"
ELEMENTS = ("Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu")
FIELDS = ("E", "mu", "coordination", "avg_nn_dists", "nn_min-max", "bader", "metadata")
CODE_COMMIT = "6dbcc598c7bea235f464bed91744c1617725b7a8"


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True,
                        help="Extracted matrio_folder directory")
    parser.add_argument("--archive", type=Path, required=True,
                        help="Original xanes_2019.zip archive for provenance")
    parser.add_argument("--destination", type=Path, default=DEST)
    parser.add_argument("--code-repository", type=Path,
                        help="Optional local TRIXS clone to confirm the pinned commit")
    args = parser.parse_args()

    if args.code_repository:
        actual = subprocess.check_output(
            ["git", "-C", str(args.code_repository), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != CODE_COMMIT:
            raise ValueError(f"TRIXS checkout {actual} does not match {CODE_COMMIT}")

    inputs = args.destination / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    sources = []
    for element in ELEMENTS:
        source_path = args.release / "spectral_data" / f"{element}_XY.json"
        output_path = inputs / f"{element}.jsonl.gz"
        count = 0
        with source_path.open() as source, output_path.open("wb") as output:
            # Empty gzip filename and zero mtime make the bytes reproducible.
            with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
                for source_row, line in enumerate(source):
                    record = json.loads(line)
                    projected = {"source_row": source_row}
                    projected.update({field: record[field] for field in FIELDS})
                    compressed.write((json.dumps(projected, separators=(",", ":"),
                                                 allow_nan=False) + "\n").encode())
                    count += 1
        sources.append({
            "element": element,
            "source_path": str(source_path.relative_to(args.release)),
            "source_sha256": sha256(source_path),
            "source_bytes": source_path.stat().st_size,
            "rows": count,
            "input_path": str(output_path.relative_to(args.destination)),
            "input_sha256": sha256(output_path),
            "input_bytes": output_path.stat().st_size,
        })
        print(f"Prepared {element}: {count} rows, {output_path.stat().st_size} bytes", flush=True)

    (inputs / "README.md").write_text(
        "# Input schema\n\n"
        "Each `<element>.jsonl.gz` is a gzip-compressed JSON Lines file. Each line "
        "describes one absorbing-site XANES spectrum for the named element. "
        "Rows retain their original order.\n\n"
        "- `source_row`: zero-based row number in the source element file.\n"
        "- `E`: photon-energy samples in eV.\n"
        "- `mu`: absorption values at the corresponding energy samples.\n"
        "- `coordination`: released absorbing-site coordination-number label.\n"
        "- `avg_nn_dists`: mean nearest-neighbor distance in angstrom.\n"
        "- `nn_min-max`: largest minus smallest nearest-neighbor distance in angstrom.\n"
        "- `bader`: released Bader-charge label in electron-charge units, or null when unavailable.\n"
        "- `metadata`: released spectrum origin and material identifier, where available.\n\n"
        "These are the earliest spectral records supplied in the open release: "
        "they have already been interpolated onto energy grids and supplied with "
        "structural labels. They are not native FEFF output or detector-raw measurements.\n"
    )
    provenance = {
        "paper_doi": "10.1038/s41524-020-00376-6",
        "data_landing_url": "https://data.matr.io/4/",
        "archive_name": args.archive.name,
        "archive_sha256": sha256(args.archive),
        "archive_bytes": args.archive.stat().st_size,
        "code_url": "https://github.com/TRI-AMDD/trixs",
        "code_commit": CODE_COMMIT,
        "source_status": "Earliest available processed spectral records; not native FEFF outputs.",
        "input_transformations": {
            "selected_fields": list(FIELDS),
            "added_fields": {"source_row": "Zero-based physical line number in source JSONL."},
            "row_selection": "All source rows, unchanged order, no filtering.",
            "values": "Selected JSON values copied without numerical transformation.",
            "compression": "gzip, compression level 9, empty filename, mtime=0.",
            "excluded": "Derived polynomial coefficients, augmentation arrays, saved splits, model outputs, and answer keys.",
        },
        "sources": sources,
        "total_rows": sum(source["rows"] for source in sources),
    }
    (args.destination / "provenance.json").write_text(
        json.dumps(provenance, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    main()
