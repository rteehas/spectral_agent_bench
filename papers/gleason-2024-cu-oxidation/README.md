# Gleason et al. (2024): Cu oxidation state from EELS and XAS

[Paper](https://doi.org/10.1038/s41524-024-01408-1) · [Open release](https://zenodo.org/records/18142209) · [Pinned source](https://github.com/smglsn12/ML_XAS_EELS/tree/85e0f34e448247f6c7a01705807dae39dd1d6cbd)

This entry contains seven independently runnable, minimal sub-questions from the paper's data preparation and spectral analysis. Each starts at its relevant stage. Inputs explicitly distinguish individual FEFF outputs, saved computational metadata, already processed simulated spectra, and digitized literature measurements. No question requires the result of another benchmark question.

| ID | Research question | Minimal inputs | Verification basis |
|---|---|---|---|
| GLEASON24-Q1 | What material-level Cu L₂,₃ spectrum is predicted for TbCu₅? | Four site/edge FEFF outputs and one structure-containing input deck | Independent released material spectrum, plus structure multiplicities |
| GLEASON24-Q2 | How much of the base set has an integer Cu label? | Saved oxidation dictionaries and record validity metadata | Separate released processed labels; saved dictionaries establish imputation provenance |
| GLEASON24-Q3 | How do stability and experimental provenance overlap? | Saved metadata and admissibility information | Separate released retained-table flags; Figure 1 is contextual |
| GLEASON24-Q4 | What cumulative model inputs correspond to Cu/Cu₂O/CuO? | Three ordinary, already aligned/normalized spectra | Cumulative arrays held back from the same release |
| GLEASON24-Q5 | What signal results from the displayed three-material combination? | Three aligned/normalized parent spectra and specified display coefficients | Recomputed weighted sum, supported by the author's embedded plot |
| GLEASON24-Q6 | How does mixture augmentation change label coverage? | Ordered base IDs/labels and reproducible sampling settings | Unchanged-author-code replay; qualitative figure comparison |
| GLEASON24-Q7 | How separated are the experimental L₃ peaks? | Three unchanged literature XAS CSVs | Independent maximum search; qualitative Figure S1 comparison |

Q2 and Q3 share an admissibility definition but answer different questions: chemical-label coverage and material-source coverage. Q4 and Q5 operate on different material trios. Q6 only asks about label coverage, so it does not unnecessarily receive thousands of spectral arrays.

## Where to review

- `../../docs/data/benchmark.json`: active review-site entry, dataset `spectral-agent-v3`.
- `paper.json`: matching per-paper snapshot for author review.
- `../../docs/data/gleason-2024-cu-oxidation/inputs/Q*/`: minimal task inputs.
- `../../docs/data/gleason-2024-cu-oxidation/verification/Q*/`: evaluator targets.
- `../../docs/data/gleason-2024-cu-oxidation/workflows/Q*.json`: worked tool sequences and actual execution logs, linked under each question's verification files.
- `../../docs/data/gleason-2024-cu-oxidation/workflows/candidate.py`: executable candidate workflows.
- `../../docs/data/gleason-2024-cu-oxidation/workflows/verify.py`: numeric checker, separate from candidate execution.
- `../../docs/data/gleason-2024-cu-oxidation/provenance.json`: exact source paths, SHA-256 hashes, projections and verification-independence statements.

The agent-facing prompt contains only necessary background, exact input descriptions and URLs, and the question/output contract. Scientific answers, reasoning, figures and worked workflows appear only on the reviewer/evaluator side. The prompts do not give target counts, inferred weights, peak positions, or completed output arrays.

## Input boundary and execution

Export a task into a new directory:

```bash
python papers/gleason-2024-cu-oxidation/export_agent_bundle.py Q1 /tmp/gleason-q1-agent
```

This exports only `prompt.txt` and the exact declared files in `inputs/`. It excludes the full paper, source solution code, verification files, reviewer reasoning and other tasks. For a benchmark run, provide this bundle to the agent. The public review site is not an access-control boundary: mount only the bundle, and restrict solution/evaluator access in the actual evaluation environment. The author-side execution audit uses separate input and verification calls but is not an OS sandbox.

Worked candidate and verification commands, from the repository root:

```bash
python docs/data/gleason-2024-cu-oxidation/workflows/candidate.py Q1 \
  --inputs /tmp/gleason-q1-agent/inputs --output /tmp/gleason-q1-agent/output
python docs/data/gleason-2024-cu-oxidation/workflows/verify.py Q1 \
  --output /tmp/gleason-q1-agent/output \
  --truth docs/data/gleason-2024-cu-oxidation/verification/Q1
```

Install the pinned dependencies in `requirements.txt` using Python 3.10. The candidate workflows never load joblib pickles, access the previous walkthrough folders, call a live API, or read verification files. Q1 uses pymatgen to identify symmetry-equivalent Cu atoms; other tasks use pandas/NumPy/Matplotlib. FEFF outputs are supplied, so a licensed FEFF executable and simulation resources are not required.

`run_candidates.py --workdir NEW_DIRECTORY` exports each input bundle, runs its candidate, invokes the verifier separately, and records commands, stdout/stderr, versions, runtime and status in `workflows/Q*.json`. Tool names are portable descriptions (shell/Python, NumPy, pymatgen and plotting), not a requirement to use a particular agent framework.

Numeric checks are necessary but not sufficient. Reviewers must also assess the requested interpretation and readable plots against each question's verification description. Style/pixel matching is not required. The candidate Python implementation emits numeric results, plots and `conclusion.md`; the worked JSON also records the scientific interpretation under `evidence`.

## Q1: scientific reconstruction rather than exact numerical replay

The Q1 background supplies the file context, material ID and a 0.01 Å positional symmetry tolerance. Interpolation, padding and endpoint choices belong to the worked candidate workflow; the agent must justify its own choices. The question no longer requests a Fermi-marker calculation.

Verification checks multiplicity-derived weights, preserves the FEFF energy/intensity conventions, and resamples the submitted spectrum onto the reference interior energies. It excludes 0.5 eV at each reference boundary and allows 2% normalized RMSE, 0.2 eV edge-peak shifts, and 5% differences in edge peak heights and areas. These are benchmark screening tolerances, not measured physical uncertainties. The comparison neither shifts nor rescales the submitted spectrum. Different output lengths and numerical treatments can pass; the archived 545-point count and optional L3 reference are not required answers. Scientific justification and the contribution plot still require review, including adjudication of other defensible treatments.

The review page presents Q1's acceptance criteria in a separate **Benchmark thresholds** component, labeled **Benchmark-defined** and **Model-generated**. These thresholds and comparison settings were generated by the model for this benchmark; they were not reported in the paper. Reference data and the worked workflow/checker have separate file lists. No numerical limits changed when this provenance was added.

`verification/Q1/comparison_policy.json` records the exact windows, thresholds and their provenance. `check_q1_variants.py` tests the released candidate and alternative linear/PCHIP interpolation, zero padding, grid spacings and endpoint choices, as well as rejected wrong weights, missing edges, shifts and normalization. Its record is `verification/Q1/variant_checks.json`.

## Ground-truth strength and known release differences

Q1–Q4 have independently stored released-output targets. Q5 is an algebraic target with an independent author plot. Q6 is an exact code-replay target for the released snapshot, **not** an independently archived historical mixture table. Q7 has an independently recomputed numeric target and a paper-supported qualitative inference; the paper does not publish the exact peak table. These distinctions are attached to the scenarios and provenance metadata.

The release and publication do not agree on every count. We preserve the released table's 3,439 base rows and its category totals. The author's figure notebook adds mixtures before drawing its label bars. Accordingly, Q2 does not grade against those bars, and Q3 does not force the published Figure 1 provenance totals. Q6 expects 5,999 realized mixtures, because one all-zero draw is skipped. Q5 preserves the displayed coefficients summing to 0.99; Q6 separately normalizes training-mixture weights.

The missing-assignment-to-zero convention is reproduced as a historical choice. It must not be interpreted as independent evidence that every zero-labeled material contains chemically Cu(0). This distinction is part of Q2's review rubric.

## Deliberately deferred questions

- Exact historical selection of the first 1,533 materials, or the added-material MP search: original query/database snapshot not recovered; current API results are not a historical answer.
- Fully independent energy-calibration fitting from the seed file: our earlier replay froze effective offsets recovered from a processed output; using them as a hidden dependency would compromise the intended input boundary. A future question can supply independently documented calibration inputs explicitly.
- Exact reconstruction of the entire combined table from all archived FEFF jobs: three incomplete edge pairs and remaining array mismatches prevent a clean exact target. Q1 deliberately uses a verified complete material with unequal site multiplicities.
- Exact Figure 2 model score, uncertainty distributions, or noise-robustness curves: not yet backed here by a separately audited training/split/model workflow. We do not present unrun candidate workflows as verified tasks.
- Reconstructing the current Materials Project oxidation-state assignment algorithm: saved dictionaries lack enough historical per-record method provenance.

## Rebuild and attribution

`prepare_assets.py --release PATH` projects minimal inputs and separately extracts verification targets from the downloaded open release. Q5/Q6 use the already audited source-code replay outputs under that release workspace. `build_entry.py` writes the site entry and workflow descriptions while retaining prior execution records. Rerun affected candidates after changing their task or verifier; a partial run preserves the other questions in the summary. These are authoring tools, not agent inputs. See `provenance.json` for the input/verification derivation of every task.

Data source: Gleason, Lu and Ciston, Zenodo record 18142209 (CC BY 4.0), outer ZIP MD5 `1246825b838f77b926d0e58f6ca68e45`. Figures are unmodified author-provided Figure 1 and Figure S1 images or embedded figure outputs from the pinned companion notebook. The article is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Minimal CSV/JSON projections are format adaptations; their prior processing and source columns are recorded. All copied assets remain attributed to the authors. No upstream notebook credentials were copied.
