# Torrisi 2020: XANES research benchmark

Q1 reproduces the published pointwise coordination-classification experiment with fixed inputs, methods and numerical acceptance. Q2–Q5 remain standalone investigations in which solvers choose and defend their analysis methods.

| Task | Research problem | Evaluation |
|---|---|---|
| Q1 | Reproduce coordination classification for classes 4, 5 and 6 | Published accuracy and per-class F1 means/SDs |
| Q2 | Neighbor-distance inference in unusually short or long environments | Numerical integrity and scientific review |
| Q3 | Incremental Bader-charge information beyond white-line position | Numerical integrity and scientific review |
| Q4 | Predictive and interpretive value of a new multiscale representation | Numerical integrity and scientific review |
| Q5 | Whether predictions and energy-localized interpretations survive intensity normalization | Numerical integrity and scientific review |

All tasks cover Ti, V, Cr, Mn, Fe, Co, Ni and Cu and can be answered independently. The earlier [question_quality_review.md](question_quality_review.md) describes the open-investigation release; its Q1 assessment is historical. Current Q1 checks are under `verification/Q1_paper/`.

## Sources and solver boundary

The source is [Torrisi et al., npj Computational Materials (2020)](https://doi.org/10.1038/s41524-020-00376-6), with the [open data release](https://data.matr.io/4/) and [TRIXS code at the audited commit](https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8). Data are CC BY 4.0: Steven B. Torrisi, Matthew R. Carbone, Brian A. Rohr, Joseph H. Montoya, Yang Ha, Junko Yano, Santosh K. Suram and Linda Hung. Released code is Apache-2.0. Hashes and field provenance are in `docs/data/torrisi-2020-xanes-rf/provenance.json`.

Export a solver-only bundle:

```bash
python papers/torrisi-2020-xanes-rf/export_agent_bundle.py Q1 --output /tmp/xanes-agent
```

Q1 exports `prompt.md`, eight prepared NPZ files and `protocol.json`. Each NPZ supplies original processed spectra, exact train/validation/test memberships, source-row IDs, and training/validation labels. Test labels, structural metadata and other targets are omitted. The protocol supplies the estimator, oversampling procedure, seeds, runtime versions and output contract, without expected scores.

Q2–Q5 each export a prompt and eight gzip JSONL files: lossless projections of all 40,907 released records in original order. Packaging does no filtering or feature construction for those tasks. Solvers choose preprocessing, models, partitions and uncertainty methods. Their output contract remains a report, figures, code, predictions and partition membership; no protocol or experiment manifest is required.

During each attempt, restrict access to that question's bundle. The repository, review website, paper, workflows and evaluator artifacts must be inaccessible. Q1 must not receive the labeled raw files supplied to Q2–Q5. The website and bundle exporter do not enforce runtime isolation.

## Q1: published experiment and fixed verification

The prepared cohort reconstructs the released spectral-quality filters and coordination labels 4/5/6 from both source populations. It preserves the 100-point post-edge-normalized arrays. Exact released memberships take precedence over the article's approximate 80/10/10 description: two successive 10% splits actually yield approximately 81/9/10.

Training-only random oversampling balances classes using seed 42 and the released row ordering. The pointwise random forest has 300 trees, maximum depth 35 and eight candidate features per split. Seeds 42–51 give ten fits per element, 80 forests and 38,610 test predictions. Complete settings and pinned NumPy/scikit-learn versions are in the input protocol.

The evaluator joins predictions to withheld original labels and calculates accuracy and F1 for each coordination class. It compares ten-fit means and population standard deviations with the author-released `pointwise_table_feff.csv`: **all 64 comparisons must agree within 0.00005 in fractional score units, plus 1e-12 arithmetic epsilon**. This is half the published table's 0.01-percentage-point rounding unit. It is a reproduction criterion, not a confidence interval or minimum prediction-quality threshold. A narrative claim cannot override a numerical failure.

An independent implementation reconstructed the experiment from raw records and archived memberships. A separate solver implementation used the prepared bundle. Both completed all 80 fits, produced identical test predictions and matched all 64 published values at printed precision using the pinned modern runtime. `reference_validation.json` and `execution_check.json` record these checks. The local audit inspected solver input access; it does not claim OS-level isolation.

The task grades the final oversampled model. It does not grade an oversampling-effect ablation: a complete published paired before/after table is unavailable. The former ExtraTrees/class-weighting example is preserved under `verification/Q1/` and is superseded.

```bash
python3 -m venv /tmp/xanes-bench-env
/tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt
OPENBLAS_NUM_THREADS=1 /tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/reproduce_coordination.py --inputs /tmp/xanes-agent/inputs --output /tmp/xanes-q1-answer --jobs 4
/tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/verify_coordination.py --inputs /tmp/xanes-agent/inputs --output /tmp/xanes-q1-answer
```

The evaluator must execute submitted source in the isolated solver environment before checking outputs. The verifier does not execute untrusted code. It checks complete prediction coverage, input/protocol declarations, oversampling counts and published comparisons; it also scores validation predictions. `adversarial_checks.json` records rejection of wrong predictions, missing/duplicate records and altered settings. Even perfectly copied test labels fail because they do not reproduce this prescribed experiment.

## Q2–Q5: open investigations

The ExtraTrees workflows remain illustrative designs, not numerical acceptance targets. They use validation-selected leaf size, two material-group holdouts, paired conditional group-bootstrap intervals and task-specific diagnostics. Alternative defensible methods and negative or mixed findings remain eligible.

```bash
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/candidate.py Q2 --inputs docs/data/torrisi-2020-xanes-rf/inputs --output /tmp/xanes-q2-answer
/tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/verify.py Q2 --inputs docs/data/torrisi-2020-xanes-rf/inputs --output /tmp/xanes-q2-answer
```

Their numerical verifier reconstructs truth, checks partitions and prediction coverage, and calculates metrics. Success returns `scientific_review_required`. Independent source execution and substantive review using `verification/scientific_review_rubric.md` remain mandatory. Published tables provide context for these four tasks rather than score thresholds. Existing execution and scientific-review receipts remain applicable to them; Q1 sections in those earlier receipts describe the superseded question.

The generic `candidate.py` and `verify.py` commands dispatch Q1 to the fixed reproduction workflow. `candidate.py ALL` runs current Q1 followed by the four open examples.

## Scientific limits

These 100-point processed spectra are the earliest released representation; native FEFF jobs, structures and detector measurements are unavailable. Q1 reproduces spectral-record holdouts. Related structures may cross partitions; forest-seed SD does not measure generalization uncertainty across new materials or experimental spectra.

For Q2–Q5, material IDs exist only for the `scrape` origin. Holding out identified materials selects a source population and cannot establish generalization to unknown-ID `feff` records. Identifier separation cannot rule out structural relatives or aliases. Worked bootstrap intervals are conditional on fitted models; two material splits provide limited sensitivity evidence. Feature-permutation effects do not establish physical causation.

## Rebuild and audit

The following rebuilds Q1 from packaged raw records and the archived source audit. Each of the two independent fitting commands trains 80 forests. Install pinned requirements first.

```bash
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/prepare_q1_reproduction.py
OPENBLAS_NUM_THREADS=1 /tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/reproduce_q1_reference.py --output /tmp/xanes-q1-reference --jobs 4 > /tmp/xanes-q1-reference.log 2>&1
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/build_q1_reference.py --reference-output /tmp/xanes-q1-reference --log /tmp/xanes-q1-reference.log
OPENBLAS_NUM_THREADS=1 /tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/reproduce_coordination.py --inputs docs/data/torrisi-2020-xanes-rf/inputs/Q1_paper --output /tmp/xanes-q1-replay --jobs 4 > /tmp/xanes-q1-replay.log 2>&1
MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/finalize_q1_reproduction.py --solver-output /tmp/xanes-q1-replay --log /tmp/xanes-q1-replay.log
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/check_q1_reproduction.py
python papers/torrisi-2020-xanes-rf/build_entry.py
python papers/torrisi-2020-xanes-rf/check_entry.py
python scripts/validate_data.py
```

For original raw-asset reconstruction, `prepare_assets.py` accepts `--release`, `--archive` and `--code-repository`; `audit_verification.py` independently checks source arrays. Preparation never executes downloaded archive code. The entry builder preserves other papers and Q2–Q5.
