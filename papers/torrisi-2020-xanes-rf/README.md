# Torrisi 2020: XANES research benchmark

Five standalone investigations test scientific study design, spectral modeling and evidence-based interpretation. Solvers receive **a question with minimal inline background/output requirements and eight raw-data files**. There are no protocol or output-schema JSON inputs. Model family, preprocessing, feature construction, splits, tuning and uncertainty methods are decisions the solver must defend.

| Task | Research problem |
|---|---|
| Q1 | Reliability for uncommon coordination environments and the value of class-imbalance treatment |
| Q2 | Neighbor-distance inference in unusually short or long environments |
| Q3 | Incremental Bader-charge information beyond white-line position |
| Q4 | Predictive and interpretive value of a newly designed multiscale spectral representation |
| Q5 | Whether predictive information and energy-localized interpretations survive intensity normalization |

All tasks cover Ti, V, Cr, Mn, Fe, Co, Ni and Cu and require evidence about previously unseen identified materials. Each can be answered independently. An independently inspected difficulty rubric is in [question_quality_review.md](question_quality_review.md); difficulty has not yet been calibrated across multiple tested systems.

## Sources and solver boundary

The source is [Torrisi et al., npj Computational Materials (2020)](https://doi.org/10.1038/s41524-020-00376-6), with the [open data release](https://data.matr.io/4/) and [TRIXS code at the audited commit](https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8). The data are CC BY 4.0: Steven B. Torrisi, Matthew R. Carbone, Brian A. Rohr, Joseph H. Montoya, Yang Ha, Junko Yano, Santosh K. Suram and Linda Hung. The code release is Apache-2.0.

The eight gzip JSONL files contain lossless projections of **all 40,907 released records**, in original order, with source-row identifiers. Packaging performs no filtering, fitting or feature construction. These 100-point processed spectra are the earliest released representation; native FEFF jobs, structures and detector measurements are unavailable. Hashes and field provenance are in `docs/data/torrisi-2020-xanes-rf/provenance.json`.

Export a solver-only bundle:

```bash
python papers/torrisi-2020-xanes-rf/export_agent_bundle.py Q3 --output /tmp/xanes-agent
```

The result contains `prompt.md` and eight files under `inputs/`. Keep the repository, review website, paper, workflows and verification artifacts inaccessible during an attempt. The review site's visual separation is not access control. The inline output contract requests enough row-level evidence to audit a chosen study; it does not prescribe an analysis recipe.

## Worked example and verification

The candidate below is **one illustrative design**, not a required solution or numeric acceptance target. It uses ExtraTrees with validation-selected leaf size, two material-group holdouts, paired conditional group-bootstrap intervals, and task-specific diagnostics. Q1 also examines record holdouts; Q4 constructs 51 quadratic multiscale coefficients and tests energy/degree reliance by held-out permutation; Q5 crosses two fitting seeds with two material partitions. These choices appear only in evaluator material.

```bash
python3 -m venv /tmp/xanes-bench-env
/tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/candidate.py ALL --inputs docs/data/torrisi-2020-xanes-rf/inputs --output /tmp/xanes-answer
/tmp/xanes-bench-env/bin/python docs/data/torrisi-2020-xanes-rf/workflows/verify.py Q1 --inputs docs/data/torrisi-2020-xanes-rf/inputs --output /tmp/xanes-answer/Q1
```

Use `Q1` through `Q5` instead of `ALL` for one independent question and a question-specific output directory. Repeat numerical verification for each generated answer. Per-question workflow JSONs record tools and commands; they are evaluator-only worked examples.

Verification has two required parts:

1. **Numerical integrity:** reconstruct truth from source labels; check record coverage, material separation, paired partitions and metric arithmetic. No fixed split, seed, model, feature ranking or reference-score agreement is required.
2. **Scientific review:** independently run submitted code and inspect leakage, fairness, uncertainty, source-population coverage and whether the question-specific evidence supports the conclusions. The mandatory rubric is `verification/scientific_review_rubric.md`. A numeric pass alone cannot establish a scientific pass.

An alternate implementation and adversarial controls are recorded in `verification/flexible_verification_v2.json`. The audit accepts a distinct model and rejects corrupted artifacts; it also demonstrates why self-consistent copied labels and fabricated auxiliary tables require source reruns and scientific checks. New worked results reside in `verification/Q1` through `Q5`; independent question, execution and scientific review receipts are stored alongside them. A separate prompt-only Q3 attempt provides a feasibility check under different scientific choices.

Raw labels provide exact truth for each submitted prediction. Author-released tables and the historical source-array audit remain contextual provenance, not acceptance targets for changed study designs. All previous fixed-recipe results are under `verification/legacy_v1` and `workflows/legacy_v1`; they are not completed answers to the revised tasks.

## Scientific limits

The released `metadata.id` is available only for the `scrape` origin. An identified-material evaluation therefore selects a source population and cannot establish generalization to unknown-ID `feff` records. The worked example reports this coverage and excludes unknown IDs from claims about new materials. Identifier separation cannot rule out structural near-duplicates or aliases without structures. Its bootstrap intervals are conditional on fitted models, and two material splits provide limited sensitivity evidence. Permutation effects describe predictive reliance under perturbed, correlated features; they do not establish physical causation.

## Rebuild and audit

```bash
python papers/torrisi-2020-xanes-rf/prepare_assets.py --release /tmp/torrisi-release/matrio_folder --archive /tmp/torrisi-xanes_2019.zip --code-repository /tmp/torrisi-trixs
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/audit_verification.py --release /tmp/torrisi-release/matrio_folder
/tmp/xanes-bench-env/bin/python papers/torrisi-2020-xanes-rf/audit_flexible_verification.py --runs /tmp/xanes-answer
python papers/torrisi-2020-xanes-rf/build_entry.py
python papers/torrisi-2020-xanes-rf/check_entry.py
python scripts/validate_data.py
```

The source-array audit reconstructs historical preprocessing solely to establish provenance. The current numerical checker uses raw labels directly. Preparation never downloads or executes archive code. The entry builder preserves the other papers and never recreates removed protocol/schema files.
