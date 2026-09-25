# Torrisi 2020: XANES structure–property benchmark

Five standalone research questions are registered in `paper.json` and the active review dataset. Each starts from the supplied spectral records, requires fresh numerical analysis and model training, and asks for an evidence-backed scientific conclusion.

| ID | Research question | Distinct analysis |
|---|---|---|
| Q1 | Does coordination prediction resolve rare environments as well as common ones? | Natural versus oversampled training, dominant-class baseline, per-class F1 and confusion matrices. |
| Q2 | How reliably do spectra determine mean neighbor distance, including distribution tails? | Regression, parity plots, training-defined tail errors and signed bias. |
| Q3 | How much local-charge information do full spectra contain beyond white-line position? | Full-spectrum versus peak-only regression, paired performance and charge parity plots. |
| Q4 | Can multiscale shape descriptors retain accuracy while identifying local-property signatures? | Construct 157 features, compare three targets, map coefficient degree and energy to model importance. |
| Q5 | Which inferred spectral signatures survive intensity normalization? | Paired normalization experiments, performance changes, rank correlation, feature overlap and coefficient-family importance. |

All eight elements (Ti, V, Cr, Mn, Fe, Co, Ni and Cu) are included. No question depends on the answer to another. Q1–Q3 probe different scientific limitations; Q4 tests representation, and Q5 tests whether interpretation depends on normalization. Shared model fits can be reused by the worked `ALL` command, but each question also runs independently.

## Sources and input boundary

- [Article](https://doi.org/10.1038/s41524-020-00376-6): S. B. Torrisi et al., *npj Computational Materials* 6, 109 (2020).
- [Data release](https://data.matr.io/4/) and [archive](https://data.matr.io/4/deployment/data/xanes_2019.zip), CC BY 4.0. Attribution: Steven B. Torrisi, Matthew R. Carbone, Brian A. Rohr, Joseph H. Montoya, Yang Ha, Junko Yano, Santosh K. Suram and Linda Hung.
- [TRIXS code](https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8), pinned at commit `6dbcc598c7bea235f464bed91744c1617725b7a8`, Apache-2.0.

`docs/data/torrisi-2020-xanes-rf/inputs/` contains lossless column projections of **all 40,907 released spectral records**, with original order and a source-row identifier. The eight gzip JSONL files are about 38 MiB together. No quality filtering, model fitting or feature construction occurs during input packaging. Array values and labels are copied without numerical alteration; hashes and preparation steps are in `provenance.json`.

These are the **earliest released spectra**, already projected onto 100 energy points, not detector-raw data or native FEFF outputs. Original structures, densities and upstream FEFF jobs are not available here. Accordingly, the questions do not ask solvers to regenerate those calculations. The released coordination and Bader labels are inputs: coordination is not inferred from the length of a neighbor list, and Bader charge is not equated with an integer oxidation state.

Solvers receive the input files, field definitions, compact comparison protocol, output schema and question text. They do not receive `workflows/`, `verification/`, the paper, published derived arrays, or worked conclusions. The review website displays evaluator material separately, but it is not access control: use the export command for an actual benchmark run.

```bash
python papers/torrisi-2020-xanes-rf/export_agent_bundle.py Q1 --output /tmp/xanes-q1-agent
```

## Executed candidate workflow

Run commands from the `spectral_agent_bench` root. Python 3.12 was used for recorded runs. `requirements.txt` pins the complete numerical environment, including the evaluator dependency pandas.

```bash
python3 -m venv /tmp/xanes-bench-env
/tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/candidate.py ALL --inputs docs/data/torrisi-2020-xanes-rf/inputs --output /tmp/xanes-answer --jobs 4
```

For an independent question, replace `ALL` with `Q1` through `Q5` and use a question-specific output directory. The program reads only the eight input spectral files, applies the declared screens, builds features and disjoint splits, fits fresh models, and calculates metrics. `summarize.py` creates the scientific comparisons, plots and conclusion from saved predictions and importances; it is called automatically. The per-question workflow JSON files name the tools, commands, outputs, source relationship and execution records.

The complete `ALL` run fits 96 distinct element/target/representation/normalization/balancing configurations, each with three random seeds. The benchmark uses **100 trees and three seeds**, compared with the original study's 300 trees and ten seeds. Its input bundle includes all 40,907 released spectral records and all eight elements; the declared quality screens precede training. These are controlled reruns, not claims of exact historical model reproduction. The published performance CSVs remain unmodified in evaluator evidence.

Numerical conventions that matter:

- Sequential 10% held-out splits produce approximately **81/9/10**, matching the notebook implementation rather than the prose's 80/10/10.
- Polynomial coefficients use each interval's **scaled [-1,1] coordinate**. The peak feature is its sample index, equivalent to energy within an element's fixed grid.
- Pointwise and polynomial forests use the source-specific `max_features` settings of 8 and 30, respectively. Q4 compares these configured pipelines; it does not isolate representation from every modeling choice.
- Oversampling happens only after splitting and only in coordination training. Q4/Q5 balance both representations for a paired comparison; the released polynomial coordination arrays were unbalanced.
- Baselines are determined from training labels only. The released plotting notebook computed its coordination modal-class baseline from held-out class counts, so the benchmark baseline need not match that plotted value.
- The validation split is reserved. No hyperparameter tuning is performed. Three-seed variation measures forest randomness on one split, not uncertainty across material families.
- Q1's no-oversampling comparison, Q2's quantile diagnostics, Q3's peak-only ablation and Q5's rank-stability summaries are benchmark extensions of the research process. Their modern reference values are labeled accordingly.

## Verification and independent reviews

```bash
/tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/verify.py Q1 --output /tmp/xanes-answer/Q1
python scripts/validate_data.py
```

Repeat verification for Q2–Q5. The checker returns a numerical screening result; a reviewer must also judge the scientific conclusion and diagnostic plots.

Ground truth has three separate origins:

1. **Released outputs:** an independently implemented audit reconstructs the raw-row preprocessing and matches all 144 released pointwise train/validation/test arrays, including labels and oversampling order. It also compares 144 polynomial vectors (157 features each) directly with the released coefficient JSON. `source_anchor_audit.json` holds the exact memberships and labels.
2. **Published numerical summaries:** four unchanged CSV tables contain the authors' FEFF-normalized and maximum-normalized pointwise/polynomial scores. They contextualize results; they are not exact targets for the smaller modern forests.
3. **Executed benchmark references:** held-back predictions and metrics cover the controlled experiments. A separate agent reruns the workflow in a clean output directory. The independent verifier recomputes metrics and scientific comparisons, fits selected models directly from released arrays, and applies positive and deliberately corrupted-output controls. Tolerances are benchmark choices, not physical uncertainty estimates.

Review evidence is in `docs/data/torrisi-2020-xanes-rf/verification/`: `question_quality_review.json`, `workflow_execution_review.json`, `verification_audit.json`, `candidate_execution.json`, `comparison_policy.json`, and source/input audits. The human-readable prompt review is `question_quality_review.md` beside this README. The preparation and audit scripts make the checks reproducible.

The fixed split is at the spectral-record level; it does not establish performance on unseen materials or experimental spectra. An exact metadata-ID audit finds that 11.6–45.9% of test records, depending on element and target, have a material identifier also present in training. This does not resolve additional structural equivalences or database aliases. Impurity importance divides credit among correlated features and supports predictive associations, not causal claims. The verifier cannot prove absence of solver leakage from outputs alone: isolate the exported input bundle and retain execution traces.

## Rebuild inputs and source anchors

After downloading/extracting the public archive and checking out the pinned code:

```bash
python papers/torrisi-2020-xanes-rf/prepare_assets.py --release /tmp/torrisi-release/matrio_folder --archive /tmp/torrisi-xanes_2019.zip --code-repository /tmp/torrisi-trixs
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/audit_verification.py --release /tmp/torrisi-release/matrio_folder
python papers/torrisi-2020-xanes-rf/build_entry.py
```

Preparation never downloads or executes archive code. It streams plain JSONL and writes deterministic gzip projections. The full 1.01-GiB source archive is not committed. `build_entry.py` updates this paper's entry and preserves other papers and the fictional examples. No publishing or deployment is performed by these commands.

After generating candidate outputs, rerun the verifier's positive/negative controls and independent archived-array model fits with:

```bash
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/audit_verification.py --runs /tmp/xanes-answer --independent-release /tmp/torrisi-release/matrio_folder
python papers/torrisi-2020-xanes-rf/check_entry.py
```
