# Gleason et al. (2024): Cu oxidation state from EELS and XAS

[Paper](https://doi.org/10.1038/s41524-024-01408-1) · [Open release](https://zenodo.org/records/18142209) · [Pinned source](https://github.com/smglsn12/ML_XAS_EELS/tree/85e0f34e448247f6c7a01705807dae39dd1d6cbd)

This entry contains seven offline questions and one draft question covering a live material search and fresh FEFF simulations. Each starts at its relevant stage. Inputs explicitly distinguish individual FEFF outputs, saved computational metadata, already processed simulated spectra, and digitized literature measurements. No question requires the result of another benchmark question. Q8 requires external runtime services and has only component-level validation so far.

| ID | Research question | Minimal inputs | Verification basis |
|---|---|---|---|
| GLEASON24-Q1 | What material-level Cu L₂,₃ spectrum is predicted for TbCu₅? | Four site/edge FEFF outputs and one structure-containing input deck | Independent released material spectrum, plus structure multiplicities |
| GLEASON24-Q2 | How much of the base set has an integer Cu label? | Saved oxidation dictionaries and record validity metadata | Separate released processed labels; saved dictionaries establish imputation provenance |
| GLEASON24-Q3 | How do stability and experimental provenance overlap? | Saved metadata and admissibility information | Separate released retained-table flags; Figure 1 is contextual |
| GLEASON24-Q4 | What cumulative model inputs correspond to Cu/Cu₂O/CuO? | Three ordinary, already aligned/normalized spectra | Cumulative arrays held back from the same release |
| GLEASON24-Q5 | What signal results from the displayed three-material combination? | Three aligned/normalized parent spectra and specified display coefficients | Recomputed weighted sum, supported by the author's embedded plot |
| GLEASON24-Q6 | How does mixture augmentation change label coverage? | Ordered base IDs/labels and reproducible sampling settings | Unchanged-author-code replay; qualitative figure comparison |
| GLEASON24-Q7 | How separated are the experimental L₃ peaks? | Three unchanged literature XAS CSVs | Independent maximum search; qualitative Figure S1 comparison |
| GLEASON24-Q8 | Which Cu materials can supply training spectra for oxidation-state prediction across different chemical environments? | Seed IDs, simulation settings, live MP access and a FEFF9 runtime | Independently captured live response; archived references only for matching structures/settings, otherwise independent evaluator FEFF runs. Draft; fresh-run validation pending |

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

Install the pinned dependencies in `requirements.txt` using Python 3.10. The Q1–Q7 candidate workflows never load joblib pickles, access the previous walkthrough folders, call a live API, or read verification files. Q1 uses pymatgen to identify symmetry-equivalent Cu atoms; the other offline tasks use pandas/NumPy/Matplotlib. FEFF outputs are supplied for those tasks. Q8 instead requires live MP access and a working FEFF9 installation; see below.

`run_candidates.py --workdir NEW_DIRECTORY` exports each input bundle, runs its candidate, invokes the verifier separately, and records commands, stdout/stderr, versions, runtime and status in `workflows/Q*.json`. Tool names are portable descriptions (shell/Python, NumPy, pymatgen and plotting), not a requirement to use a particular agent framework.

Numeric checks are necessary but not sufficient. Reviewers must also assess the requested interpretation and readable plots against each question's verification description. Style/pixel matching is not required. The candidate Python implementation emits numeric results, plots and `conclusion.md`; the worked JSON also records the scientific interpretation under `evidence`.

## Q1: scientific reconstruction rather than exact numerical replay

The Q1 background supplies the file context, material ID and a 0.01 Å positional symmetry tolerance. Interpolation, padding and endpoint choices belong to the worked candidate workflow; the agent must justify its own choices. The question no longer requests a Fermi-marker calculation.

Q1's Ground truth reasoning presents the executed solution as eight numbered steps, naming the programs, operations and resulting outputs: pymatgen structure/symmetry analysis, NumPy edge interpolation/combination and site averaging, pandas/JSON output, Matplotlib plotting, and a separate evaluator check. The displayed steps and the workflow JSON are generated from the same definitions in `build_entry.py`; the recorded execution is preserved. These worked-solution details are excluded from the agent prompt.

Verification checks multiplicity-derived weights, preserves the FEFF energy/intensity conventions, and resamples the submitted spectrum onto the reference interior energies. It excludes 0.5 eV at each reference boundary and allows 2% normalized RMSE, 0.2 eV edge-peak shifts, and 5% differences in edge peak heights and areas. These are benchmark screening tolerances, not measured physical uncertainties. The comparison neither shifts nor rescales the submitted spectrum. Different output lengths and numerical treatments can pass; the archived 545-point count and optional L3 reference are not required answers. Scientific justification and the contribution plot still require review, including adjudication of other defensible treatments.

The review page presents Q1's benchmark-defined acceptance criteria as plain notes at the end of Verification, after the reference data and worked workflow/checker. Each setting has a bold title, such as **Maximum Normalized RMSE:**. The introductory note states: "Note, the screening thresholds and comparison settings below were not reported in the paper and are not physical uncertainty estimates. They were produced separately during the labeling process." The structured metadata retains their benchmark-defined, model-generated provenance. No numerical limits changed when these notes were reformatted.

`verification/Q1/comparison_policy.json` records the exact windows, thresholds and their provenance. `check_q1_variants.py` tests the released candidate and alternative linear/PCHIP interpolation, zero padding, grid spacings and endpoint choices, as well as rejected wrong weights, missing edges, shifts and normalization. Its record is `verification/Q1/variant_checks.json`.

## Ground-truth strength and known release differences

Q1–Q4 have independently stored released-output targets. Q5 is an algebraic target with an independent author plot. Q6 is an exact code-replay target for the released snapshot, **not** an independently archived historical mixture table. Q7 has an independently recomputed numeric target and a paper-supported qualitative inference; the paper does not publish the exact peak table. These distinctions are attached to the scenarios and provenance metadata.

The release and publication do not agree on every count. We preserve the released table's 3,439 base rows and its category totals. The author's figure notebook adds mixtures before drawing its label bars. Accordingly, Q2 does not grade against those bars, and Q3 does not force the published Figure 1 provenance totals. Q6 expects 5,999 realized mixtures, because one all-zero draw is skipped. Q5 preserves the displayed coefficients summing to 0.99; Q6 separately normalizes training-mixture weights.

The missing-assignment-to-zero convention is reproduced as a historical choice. It must not be interpreted as independent evidence that every zero-labeled material contains chemically Cu(0). This distinction is part of Q2's review rubric.

## Q8: training spectra across Cu chemical environments

The research motivation is to predict average Cu oxidation state from XAS and EELS across different compounds. Local chemistry also affects Cu spectral shape, making varied Cu environments relevant to the training set. Additional Materials Project structures provide sources of simulated examples beyond the seed collection; experimental structure provenance or predicted stability focuses the search on potentially experimentally accessible materials. The resulting spectra are candidates for later alignment, oxidation-state labeling and training. This subquestion does not establish an improvement in model accuracy or quantify coverage gaps in the seed set.

The agent searches the full current Cu-containing Materials Project catalog, saves a response snapshot, selects eligible materials and excludes valid seed IDs. It then chooses three representative additions, explains their chemical and Cu-environment variety, and performs both edges at every inequivalent Cu site. A case with multiple Cu environments exercises the averaging step. The three-material scope keeps simulation cost bounded while retaining the search and structure-to-spectrum workflow.

Export Q8 with `export_agent_bundle.py Q8 NEW_DIRECTORY`. Its bundle contains only seed IDs, simulation settings and the prompt. Configure `MP_API_KEY` and a local FEFF9 driver through `FEFF_COMMAND` in the benchmark runtime. The candidate program `workflows/search_and_simulate.py` has four stages, each taking `--inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY`: `search`, `prepare`, `run`, and `collect`. The driver runs in each job directory, reads `feff.inp`, writes `xmu.dat`, and must stream the FEFF version/convergence log to stdout. No author submission scripts are executed, and no credentials are copied from upstream notebooks.

`prepare_q8_assets.py` projects seed IDs and extracts three evaluator reference cases from the open release. `check_q8_setup.py` tests OR selection and seed exclusion, generates eight input decks from archived structure headers, checks the decks, and reconstructs the three separately released material curves from archived raw outputs. The latter is explicitly a postprocessing test, not new simulation. The program refuses to run FEFF over pre-existing `xmu.dat` files. These checks are recorded in `verification/Q8/setup_checks.json` and the Q8 workflow record.

**Execution status: partially validated.** The live query and fresh FEFF9 calculations have not been run in this environment because no runtime credential or FEFF executable is configured. Q8 is excluded from the offline candidate suite; export checks report this limitation instead of claiming a full pass. The evaluator must capture the live response independently, verify query completeness and material eligibility, and obtain independent FEFF reference results for structures/settings without a matching archived reference. Today’s MP IDs alone do not establish that archived and current structures are identical. Numerical simulation tolerances need pilot calibration before scoring.

Historical compute evidence is in `verification/Q8/runtime_audit.json`: 6,839 timestamped jobs on 36 ranks total roughly 13,776 allocated core-hours, excluding 359 incompletely timed logs. The three archived examples (KCu₄Se₃, TbCu₅, CuTe₂) total 956 seconds if their eight jobs run sequentially on that allocation, or 9.56 allocated core-hours. These are historical timings, not a guarantee for new hardware or newly selected materials. A fresh pilot should establish the runtime budget and numerical comparison policy.

## Deliberately deferred questions

- Exact historical selection of the first 1,533 materials, or exact recovery of the original additional-material MP query: the original database snapshot was not recovered. Q8 implements a new live search and captures its own snapshot; it does not claim historical membership equivalence.
- Fully independent energy-calibration fitting from the seed file: our earlier replay froze effective offsets recovered from a processed output; using them as a hidden dependency would compromise the intended input boundary. A future question can supply independently documented calibration inputs explicitly.
- Exact reconstruction of the entire combined table from all archived FEFF jobs: three incomplete edge pairs and remaining array mismatches prevent a clean exact target. Q1 deliberately uses a verified complete material with unequal site multiplicities.
- Exact Figure 2 model score, uncertainty distributions, or noise-robustness curves: not yet backed here by a separately audited training/split/model workflow. We do not present unrun candidate workflows as verified tasks.
- Reconstructing the current Materials Project oxidation-state assignment algorithm: saved dictionaries lack enough historical per-record method provenance.

## Rebuild and attribution

`prepare_assets.py --release PATH` projects minimal inputs and separately extracts verification targets from the downloaded open release. Q5/Q6 use the already audited source-code replay outputs under that release workspace. `build_entry.py` writes the site entry and workflow descriptions while retaining prior execution records. Rerun affected candidates after changing their task or verifier; a partial run preserves the other questions in the summary. These are authoring tools, not agent inputs. See `provenance.json` for the input/verification derivation of every task.

Data source: Gleason, Lu and Ciston, Zenodo record 18142209 (CC BY 4.0), outer ZIP MD5 `1246825b838f77b926d0e58f6ca68e45`. Figures are unmodified author-provided Figure 1 and Figure S1 images or embedded figure outputs from the pinned companion notebook. The article is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Minimal CSV/JSON projections are format adaptations; their prior processing and source columns are recorded. All copied assets remain attributed to the authors. No upstream notebook credentials were copied.
