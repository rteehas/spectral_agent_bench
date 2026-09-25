# Commands

The independent analysis used only `/tmp/torrisi-open-q3-solver/prompt.md` and its eight `inputs/*.jsonl.gz` files as task-specific information. The supplied Python environment was used for numerical libraries. No benchmark code, paper, evaluator, reference output, web material, or other agents' analysis was read.

Initial inspection read the prompt, listed its input files, and used Python `gzip`, `json`, `collections`, and `numpy` to inspect field presence, finite values, per-element energy grids, ID/origin coverage, label ranges, and exact duplicate absorption arrays. A syntax check used:

```bash
/tmp/torrisi-env/bin/python -m py_compile /tmp/torrisi-open-q3-answer/code/analyze.py
```

The actual fit command was:

```bash
/tmp/torrisi-env/bin/python /tmp/torrisi-open-q3-answer/code/analyze.py \
  --inputs /tmp/torrisi-open-q3-solver/inputs \
  --output /tmp/torrisi-open-q3-answer --workers 4 \
  > /tmp/torrisi-open-q3-answer/execution.log 2>&1
```

The audit and additional fixed-first-split bootstrap command was:

```bash
/tmp/torrisi-env/bin/python /tmp/torrisi-open-q3-answer/code/audit_and_summarize.py \
  --inputs /tmp/torrisi-open-q3-solver/inputs \
  --output /tmp/torrisi-open-q3-answer \
  > /tmp/torrisi-open-q3-answer/audit.log 2>&1
```

To rerun elsewhere, create a Python environment, install `code/requirements.txt`, and substitute paths in those last two commands. `design.json` records exact software versions and input SHA-256 checksums. `execution.log` records every completed split. Modeling uses deterministic recorded seeds; minor platform/library numerical differences remain possible. The first-split multiple-comparison sensitivity uses a separate fixed bootstrap seed and does not alter or select models.

The report was rendered after the completed audit:

```bash
/tmp/torrisi-env/bin/python /tmp/torrisi-open-q3-answer/code/write_report.py --output /tmp/torrisi-open-q3-answer
```

The audit was rerun after adding the material-overlap diagnostic; model fits and predictions were unchanged. The uncertainty figure was visually inspected. All code files passed a final Python syntax check.
