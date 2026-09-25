# Szymanski 2024: open scientific research benchmark

This entry contains five open research questions. Solvers receive native numeric spectra, raw labels and a self-contained prompt. They must choose and justify their models, preprocessing, validation, combination methods, perturbations and uncertainty analysis. There is no supplied protocol or separate output-schema file. Q5 adds an upstream discovery task that does not name the target representation.

| ID | Scientific question | Decisions left to the solver |
|---|---|---|
| Q1 | Does representation offer a reproducible advantage for phase identification? | Valid evaluation, learner/analysis sensitivity, complementary errors and integration. |
| Q2 | Can both constituent identities and phase count be inferred from mixtures? | Reference construction, calibration, variable-cardinality inference and failure analysis. |
| Q3 | Which real-space interval preserves identification under noise/background? | Perturbation realism, window selection, predictive discrimination and generalization of the choice. |
| Q4 | Does virtual-PDF evidence help detect experimental secondary phases? | Transfer from simulations, full-library identification, integration, false positives and abundance-dependent claims. |
| Q5 | How can ordinary diffraction identify phases more reliably without additional measurements? | Diagnose limitations, propose physical hypotheses, compare remedies, and test their mechanism and utility. The solver is not told to use PDFs. |

These are intended to test scientific problem formulation and execution by a multi-agent system. A short reference script is not supplied to the solver. The illustrative candidate deliberately makes its own choices, and a different defensible analysis may reach different numerical results. Difficulty has not been calibrated by measuring a population of systems; the evidence here establishes feasibility, source grounding and reviewability.

The linked study concerns **powder XRD and virtual PDFs**, not XANES. These questions derive from its research stages, but do not require the paper as an input and do not claim to reconstruct its historical CNN scores.

## Sources and available data

- Nathan J. Szymanski, Sean Fu, Ellen Persson and Gerbrand Ceder, [article](https://doi.org/10.1038/s41524-024-01230-9), *npj Computational Materials* 10, 45 (2024), CC BY 4.0.
- Nathan Szymanski (2023), [Figshare version 1](https://doi.org/10.6084/m9.figshare.24043410.v1), CC BY 4.0. `Data.zip` is 264,508,800 bytes; SHA256 `92194b2523dec90b7cbf88a30d997bf5456284910e4af2b46586835cf6c4da24`.
- [Inspected source snapshot](https://github.com/njszym/XRD-AutoAnalyzer/tree/bf32082521e45c0fcf5cf9ae9bd1321e76bf9012), commit `bf32082521e45c0fcf5cf9ae9bd1321e76bf9012`, MIT. This is not asserted to be a paper-era commit.

The archive contains 2,690 simulations and 240 measured patterns: 560 single-phase Li-La-Zr-O spectra (28 phase IDs), 530 single-phase Li-Ti-P-O spectra (53 IDs), 800 mixtures per chemistry, and 120 experimental mixtures per chemistry. Those counts differ from the complete historical study. The archive lacks the original model splits, per-sample CNN outputs, ordering sweep and separately categorized artifact data. Q3 therefore asks for a new controlled perturbation study, with independent held-out predictive evaluation.

All 2,930 native numeric arrays are preserved at float64 precision. Simulations span 10–140° on 6,139 points. Experimental axes span approximately 10–80° with two slightly different grids. One experimental filename has an inconsistent scan-range label; numeric axes are authoritative. “Raw” means earliest released numeric spectra; simulated spectra already contain augmentations and experimental detector frames are unavailable.

All records now use opaque IDs. Two- and three-phase simulations are pooled into `Mixtures.npz`; filenames and IDs do not encode cardinality. The single-phase tables have no predefined train/test split. Q4 supplies the full same-chemistry simulation library rather than the four formulas known to occur in its measured targets. Preparation labels are only used for final scientific scoring.

## Prompt and input boundary

Q1–Q4 directly state only the data/label semantics, wavelength, virtual-PDF definition, research objective, evaluation boundary and compact output contract. Q5 omits the representation name, definition and mathematical hints. No learner, parameter, grid, normalization, partition, fusion, perturbation magnitude or distance window is prescribed. Output formatting enables independent checks and does not define the analysis.

For Q1–Q4, predictions need only source ID, representation and predicted labels; the partition table needs source ID and role. Method and fold identifiers are needed only to distinguish multiple comparisons. Q3 also records its experimental conditions. Constant condition labels, aggregate grouping labels and a separate metrics table are not requested. The evaluator derives chemistry, phase-count and abundance strata from source metadata and computes its own metrics. Quantitative findings and uncertainty remain part of the scientific report. Q5's freely named methods and condition descriptions are covered below.

```bash
python papers/szymanski-2024-xrd-pdf/export_agent_bundle.py Q1 --output /tmp/xrd-q1-agent
```

Exports contain only `task.json` and the relevant raw NPZ/label JSON files. There is no supplementary instructions file, worked code, expected prediction, evaluator report or paper text. Attribution is included in `task.json`. The review website displays evaluator materials separately but provides no access control; isolate exported bundles for benchmark use.

**Evaluation labels are readable.** They are needed for an agent to produce its own scientific comparisons. Excluding them from inference is an audited research requirement, not an enforced blinded execution environment. An output-only check cannot prove the absence of label leakage. Review submitted code, execution evidence and any tuning decisions; using target labels or target cardinality to set predictions invalidates the analysis.

## Q5: discovery without naming the target

Q5 presents the problems that motivate a new approach: possible over-reliance on dominant peaks and sensitivity to measurement artifacts. The solver must establish whether these limitations occur, propose a physically justified remedy, and investigate whether it works. It can choose representations, preprocessing, models or combinations. Neither a particular remedy nor a positive result is prescribed.

```bash
python papers/szymanski-2024-xrd-pdf/export_agent_bundle.py Q5 --output /tmp/diffraction-discovery-task
```

The solver directory contains only a neutrally identified task and four native single-phase input files. Creator/license credit remains in the task. The full source title, DOI and attribution are retained in the adjacent **operator-only** `/tmp/diffraction-discovery-task.provenance.json`; keep that record with the exported data when distributing it to benchmark operators. Do not include that sibling record in the solver's mounted directory or context.

Run Q5 in a fresh context with only that directory and the numerical tools it needs. Exclude the paper, the public review page, Q1–Q4, worked code and evaluator files, and disable external retrieval for the unassisted-discovery track. Those materials reveal the target. The exporter does not enforce filesystem/network isolation; benchmark operators must do so. Creator credit and the data themselves can still permit source recognition, and prior model knowledge cannot be excluded. Record any known exposure and treat paper-assisted runs separately.

The [discovery rubric](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_rubric.md) records **scientific quality** and **target-discovery stage** separately. A valid alternative can earn scientific credit without reaching the virtual-PDF target. Naming a PDF earns no target credit by itself: the assessor checks physical reasoning, implementation, held-out validation and mechanistic evidence. An honestly demonstrated lack of benefit does not erase a correct discovery and investigation. Source-derived predictive performance is reported separately from both judgments; there is no required accuracy or improvement threshold.

The worked Q5 analysis is written with prior knowledge of the target. It establishes feasibility and provides auditable example evidence; it does not show that an uninformed system discovered the idea. Actual discovery performance remains to be measured.

```bash
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/discovery-mpl /tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/discovery_candidate.py --inputs /tmp/diffraction-discovery-task/inputs --output /tmp/discovery-answer
/tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/verify_discovery.py --output /tmp/discovery-answer
```

Q5 predictions use freely chosen `method` identifiers rather than a prescribed representation vocabulary. Source IDs, predicted phases and source partitions support numerical checks. Named experimental conditions need descriptions; saved generated evidence and report claims require code and scientific review. The checker cannot establish conceptual discovery or verify every physical claim from output tables alone.

The [question review](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_quality_review.json) checks that the neutral export withholds the target. The [execution review](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_execution_review.json) reproduces all 15 deterministic worked outputs. The [verification audit](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_audit.json) exercises invalid submissions and alternative methods. An [independent physical audit](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_physics_review.json) reconstructs transforms, perturbations, ablations, metrics and uncertainty from source arrays without importing the candidate code. The [scientific assessment](../../docs/data/szymanski-2024-xrd-pdf/verification/discovery_scientific_review.md) records evidence and limitations separately from the author's known exposure to the target.

Reproduce the evaluator's audits with the unpacked release and worked output:

```bash
OPENBLAS_NUM_THREADS=1 /tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/audit_discovery.py --release /path/to/Data --candidate-output /tmp/discovery-answer
OPENBLAS_NUM_THREADS=1 /tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/audit_discovery_physics.py --candidate-output /tmp/discovery-answer
```

## Worked example, separate from the task

From the repository root, using Python 3.12:

```bash
python3 -m venv /tmp/xrd-bench-env
/tmp/xrd-bench-env/bin/python -m pip install -r papers/szymanski-2024-xrd-pdf/requirements.txt
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xrd-mpl /tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/candidate.py ALL --inputs docs/data/szymanski-2024-xrd-pdf/inputs --output /tmp/xrd-answer
```

For one question, replace `ALL` with Q1–Q4; its `--output` is then the question directory itself. The per-question workflow records identify the tool calls, analysis choices and source relationship. Candidate outputs under `verification/Qn/` illustrate a valid way to investigate each question. They are **not exact answer keys** or required performance thresholds.

The candidate makes its own train/validation/test partitions, compares learner families for Q1, calibrates variable-cardinality mixture inference on generated validation mixtures for Q2/Q4, and selects a Q3 distance window on validation classification before testing it. Numerical and methodological choices are documented in the candidate's report/design files only. Its results describe those experiments, not universal superiority of a representation.

## Verification has two separate stages

```bash
/tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/verify.py --question Q1 --output /tmp/xrd-answer/Q1
/tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/check_entry.py
python scripts/validate_data.py
```

Repeat the first command for Q2–Q4.

The automatic checker recovers labels from original release filenames, verifies source-record partitions, checks prediction coverage and allowed labels, and independently computes metrics from predictions. If a supplemental metrics table uses the worked example's recognized format, its arithmetic is checked too; other report tables require scientific review. It does not load the candidate's predictions or require its estimator, split, transforms, score fusion, windows or outcomes. Additional source audits compare every packaged spectrum against its original release member. Positive controls exercise alternative methods/splits and minimal submissions; negative controls test corrupted submissions.

A separate [scientific rubric](../../docs/data/szymanski-2024-xrd-pdf/verification/scientific_review_rubric.md) evaluates design validity, physical/numerical treatment, evaluation and uncertainty, evidence-supported conclusions, and reproducibility. The automatic verdict is **submission integrity only**. A poor or trivial model can submit arithmetically consistent predictions and still fail scientific review. Unsupported causal claims, target leakage or fabricated evidence cannot pass by matching a numerical table.

Three independent reviews cover question difficulty/context, fresh execution of the worked examples and verification correctness. Q3 must show held-out phase discrimination; smooth-looking transforms or energy retention alone are insufficient. Q2 must infer cardinality; Q4 must not exploit the measured sample labels to restrict the reference library. Negative scientific findings are valid when supported.

The [worked-example scientific review](../../docs/data/szymanski-2024-xrd-pdf/verification/scientific_review.md) records evidence and deductions for each question. The [verification audit](../../docs/data/szymanski-2024-xrd-pdf/verification/verification_audit.json) records source comparisons and corrupted/alternative submission controls. An additional [independent numerical audit](../../docs/data/szymanski-2024-xrd-pdf/verification/independent_candidate_evidence_review.json) reconstructs the worked Q3 transforms and perturbations; its candidate-specific checks are not requirements for alternative methods.

## Rebuild and audit

```bash
/tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/prepare_assets.py --release /path/to/Data --archive /path/to/Data.zip
python papers/szymanski-2024-xrd-pdf/build_entry.py
OPENBLAS_NUM_THREADS=1 /tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/audit_verification.py --release /path/to/Data --candidate-runs /tmp/xrd-answer
OPENBLAS_NUM_THREADS=1 /tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/independent_candidate_review.py --candidate-runs /tmp/xrd-answer
```

The other paper entries are preserved. The dataset release ID changes because the questions, inputs and evaluation meaning have changed. The previous fixed-protocol revision remains in Git history; it is not presented as validation of the new tasks.
