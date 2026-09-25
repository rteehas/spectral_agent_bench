# Szymanski 2024: diffraction representation benchmark

Four independently executable research questions are registered in `paper.json` and the active review dataset. **The linked paper concerns XRD and virtual PDFs, not XANES.**

| ID | Research question | Distinct work |
|---|---|---|
| Q1 | Which representation identifies held-out single-phase patterns more reliably? | Train fresh ridge classifiers, compare representations and score fusion, analyze paired errors. |
| Q2 | How does constituent recovery change from two to three phases? | Construct reference templates from training spectra, solve nonnegative fits, score exact sets and constituent recovery. |
| Q3 | How do noise and smooth background affect different distance windows? | Generate paired perturbations of 11 raw Li2TiO3 realizations, transform them, measure distortion and retained signal. |
| Q4 | Can simulated references recover minor phases in measured mixtures? | Transfer to 240 experimental patterns and evaluate formula-level identification versus secondary abundance. |

The questions are controlled baseline experiments derived from distinct stages of the research process. They require fresh computation on raw released spectra. **They do not reproduce the original trained CNNs or their historical scores.** No question requires another question's answer. Q2/Q4 share definitions of training partitions and template fitting, which each standalone workflow reconstructs itself.

## Sources and what is actually available

- Nathan J. Szymanski, Sean Fu, Ellen Persson and Gerbrand Ceder, [article](https://doi.org/10.1038/s41524-024-01230-9), *npj Computational Materials* 10, 45 (2024), CC BY 4.0.
- Nathan Szymanski (2023), [Figshare version 1](https://doi.org/10.6084/m9.figshare.24043410.v1), CC BY 4.0. Archive `Data.zip`, 264,508,800 bytes; SHA256 `92194b2523dec90b7cbf88a30d997bf5456284910e4af2b46586835cf6c4da24`.
- [XRD-AutoAnalyzer source](https://github.com/njszym/XRD-AutoAnalyzer/tree/bf32082521e45c0fcf5cf9ae9bd1321e76bf9012), pinned at `bf32082521e45c0fcf5cf9ae9bd1321e76bf9012` (MIT). This is the inspected current snapshot, not an asserted paper-era commit. No upstream code is executed by preparation.

The archive contains **2,690 simulations and 240 experiments**: 560 single-phase Li-La-Zr-O patterns (28 phase IDs), 530 single-phase Li-Ti-P-O patterns (53 IDs), and 400 two-phase plus 400 three-phase patterns in each chemistry. These counts differ from the paper's 8,000-pattern study and its 45-ID Li-Ti-P-O model. The release does not contain separate ordering-sweep or categorized-artifact datasets, original training splits, per-sample CNN predictions or CAM arrays. Those unavailable analyses are not offered as exact-reproduction tasks.

All simulated traces contain 6,139 points spanning 10–140°. Experimental files have either 6,442 points spanning approximately 10.003–79.994° or 6,452 points spanning approximately 9.995–80.095°. One source filename says `02-80` despite its native axis matching the other measured scans. Numerical axes, rather than names, determine the analysis interval.

`docs/data/szymanski-2024-xrd-pdf/inputs/` preserves every native numeric value at float64 precision. Simulation axes are deduplicated within NPZ files; intensities remain unchanged. Experimental arrays retain both columns. IDs replace answer-bearing filenames, and raw labels are separated into metadata. The raw-value audit checks all 2,930 arrays against the release. Here “raw” means the earliest released numeric spectra, not detector frames; the simulated spectra already contain augmentations. Inputs occupy about 136 MiB.

## Solver boundary

Solvers receive only raw arrays, record/label metadata, necessary numerical conventions, output schema and the question. Labels are supplied for scientific evaluation; target labels must not enter feature construction or inference. The reference code predicts first and scores afterward. Output-only checks cannot prove label separation, so retain execution traces. The public review site separates evaluator files visually, **not by access control**. Export and isolate the question for benchmark use:

```bash
python papers/szymanski-2024-xrd-pdf/export_agent_bundle.py Q1 --output /tmp/xrd-q1-agent
```

The export omits worked code, source filenames, expected outputs and evaluator files. It trims protocol sections to those needed by the question. Supervised training/evaluation labels remain available, as required for the scientific comparison.

## Executed workflow

Run from the `spectral_agent_bench` root. Recorded executions use Python 3.12 and the pinned numerical packages in `requirements.txt`.

```bash
python3 -m venv /tmp/xrd-bench-env
/tmp/xrd-bench-env/bin/python -m pip install -r papers/szymanski-2024-xrd-pdf/requirements.txt
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xrd-mpl /tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/candidate.py ALL --inputs docs/data/szymanski-2024-xrd-pdf/inputs --output /tmp/xrd-answer
```

Replace `ALL` with Q1–Q4 to run one question; for a single question, `--output` is that question's output directory. Outputs include numerical predictions or perturbation curves, recomputed metrics, a raw-linked transform probe, a plot and an evidence-backed conclusion. The per-question `workflows/Qn.json` files give the tool calls and stages.

The baseline conventions are explicit because the paper's prose, current code and raw archive differ:

- All tasks use 2,001 points on the common supported 10.02–79.98° range, a 10th-percentile intensity baseline and peak scaling. Negative residual intensities are retained. This differs from upstream smoothing/rolling-ball preprocessing.
- Virtual PDFs use `(2/pi) integral Q*I(Q)*sin(Q*r) dQ`, matching the inspected code's uncorrected transform rather than the paper equation's `S(Q)-1`. No form-factor correction is implied. Classification uses 1,000 r points from 1–40 Å; Q3 extends to 120 Å. The independent verifier reconstructs this transform directly.
- Q1 holds out the last native replicate indices within every phase, using a deterministic approximately 70/30 split. It tests new augmented realizations of represented phases, not unseen phases. Softmax-transformed ridge scores are uncalibrated.
- Q2 uses the true number of phases, and tests identity recovery conditional on that information. Templates use only the single-phase training subset. Two-/three-phase cohorts also differ in their component combinations and amounts, so differences do not isolate a causal crowding effect.
- Q3 generates new perturbations of already augmented spectra. It examines signal/artifact energy, not classifier accuracy or historical robustness scores. Half-open distance windows avoid double-counting boundary samples.
- Q4 is restricted to four reagent formulas per chemistry and merges polymorphs for formula-level evaluation. It does not score the correct polymorph or infer mass fractions from fit coefficients. Twelve ordered mixtures per chemistry/abundance share component identities, limiting independence and precision.

## Verification and independent review

```bash
/tmp/xrd-bench-env/bin/python docs/data/szymanski-2024-xrd-pdf/workflows/verify.py --question Q1 --output /tmp/xrd-answer/Q1
/tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/check_entry.py
python scripts/validate_data.py
```

Repeat the verifier for Q2–Q4. The numerical loop has independent anchors:

1. **Released ground truth:** original source filenames encode simulated phase sets and experimental preparation compositions. The evaluator independently parses these, rather than trusting the candidate's labels. Native array preservation is checked against every release file.
2. **Independent mathematics:** the verifier reconstructs the sine transform and Q3 perturbations without importing the candidate. Selected ridge and nonnegative fits are independently checked where documented in the audit.
3. **Modern reference outputs:** deterministic baseline predictions/metrics are stored under `verification/Qn`. They are benchmark-generated results, not author-released historical predictions. Agreement tolerances are numerical reproducibility criteria, not scientific confidence intervals.
4. **Controls and review:** a separate agent executes each workflow using copied code and minimal input-only bundles. Another agent audits source anchors and tests deliberately corrupted outputs. A third reviews question design, necessary context, nontriviality and neutrality. The reports are linked from each review entry.

Numerical success must be accompanied by inspection of plots and scientific interpretation. Alternative valid analysis methods may need manual evaluation; the automatic checker targets the declared fixed protocol. This scope does not establish general CNN superiority, unknown-phase detection or a universal experimental detection limit.

## Rebuild

Download and extract the public archive, then run:

```bash
/tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/prepare_assets.py --release /path/to/Data --archive /path/to/Data.zip
python papers/szymanski-2024-xrd-pdf/build_entry.py
```

The source archive and repository checkout are not committed. The review entry keeps the other papers intact and changes the dataset release ID so prior reviews are not silently reused. These commands do not publish the website.

To repeat the independent source audit, model refits and corrupted-output controls after a rerun:

```bash
OPENBLAS_NUM_THREADS=1 /tmp/xrd-bench-env/bin/python papers/szymanski-2024-xrd-pdf/audit_verification.py --release /path/to/Data --candidate-runs /tmp/xrd-answer
```
