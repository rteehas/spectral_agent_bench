# Guo 2023: sulfur XANES research questions

Three independent tasks use native site spectra and VASP calculation records from
the open lithium-thiophosphate release. Each task is an open scientific question;
the solver receives minimal format/energy-reference context and raw inputs, with
no processing script, expected conclusion, model, cutoff, broadening protocol or
worked answer.

| Task | Research question | Substantial decisions left to the solver |
|---|---|---|
| Q1 | When do interchangeable-site assumptions distort material fingerprints? | Reconstruct material responses; isolate site energy/population effects; assess resolution sensitivity and exceptions. |
| Q2 | Does local lithium coordination reliably predict a sulfur-edge red shift? | Define neighbors and shifts; address phosphorus/composition confounding; test robustness and interpretation. |
| Q3 | Does spectral inference of phosphorus coordination generalize to unseen glasses? | Establish labels from geometry; design crystal/glass transfer; assess rare environments, resolution and dependent observations. |

The tasks derive from the database construction, structural interpretation and
proposed local-environment use of [Guo et al., Scientific Data (2023)](https://doi.org/10.1038/s41597-023-02262-4).
Q2 and Q3 are new analyses supported by its release, not claimed reproductions of
historical regressions or machine-learning results. They test substantial steps
in a scientific investigation. Difficulty is intended, not empirically calibrated
against a population of solver systems.

## Data and truth

The [Materials Cloud v3 release](https://doi.org/10.24435/materialscloud:6z-qm)
contains 66 structures (48 glassy, 18 crystalline) and 2,681 inequivalent-site
spectra. Numeric columns are the cropped native VASP energy and three diagonal
dielectric components, not raw detector counts. The eight solver files preserve
all released numeric values as float64 and unchanged calculation text. The
original material index is retained. [Provenance](../../docs/data/guo-2023-sulfur-xas/provenance.json)
records source archive SHA256, every original input-file hash and packaged hashes.
The data license is CC BY4.0; Guo and coauthors are credited in every export.

The independently held-back `released_material_spectra.npz` contains the authors'
66 unbroadened material outputs. All were independently reconstructed from raw
inputs to approximately3.1e-12 maximum relative L2 error. The alignment is
`E_native + E0_corehole - (N_corehole/N_neutral)*E0_neutral - E_Fermi`.
Multiplicity-weighted cubic interpolation reproduces the release; physical
orientational averages differ by an allowed intensity scale. The energy origin
is not experimentally calibrated. Core-hole POSCAR atom0 is the absorber;
directory multiplicities are reduced ratios, not supercell atom counts.

[xas-tools v0.1.0](https://github.com/atomisticnet/xas-tools/releases/tag/v0.1.0),
commit `a7d08913fc59d6509459268279b33195cf20e30b`, was inspected independently.
Its parser omits the Fermi subtraction that the released output demonstrably
requires; its spectrum accessor also mutates accumulated intensities. The worked
candidate therefore implements explicit parsing and averaging. The tag's
broadening examples differ from the article, and the released broadened/shifted
averages have additional undocumented normalization/calibration. They are not
used as exact numerical truth. The [source-code audit](../../docs/data/guo-2023-sulfur-xas/verification/source_audit/release_code_audit.md)
and [independent reconstruction results](../../docs/data/guo-2023-sulfur-xas/verification/source_audit/reconstruction_results.json)
are evaluator-only.

The release does not include the experimental Li2S/P2S5/NiS reference arrays,
self-absorption processing, charge densities or convergence sweeps. No task
requires them or claims to reproduce those parts of the paper. No VASP executable
or licensed pseudopotentials are needed: the calculations have already run.

## Solver isolation

From the repository root:

```bash
python3 papers/guo-2023-sulfur-xas/export_agent_bundle.py Q1 --output /tmp/guo-Q1-agent
```

Replace Q1 with Q2/Q3. The export contains only `task.json` and eight input files.
Supply this directory in a fresh isolated context. Keep the review website,
source paper, code release, reference averages, candidate workflows and verifier
outside the solver's accessible files. The website separates these fields but
provides no access control. Source attribution is retained; benchmark runs should
disable external retrieval that could follow it to held-back outputs. This does
not eliminate prior model knowledge.

Q3 structures and labels remain readable so a solver can conduct its own
scientific evaluation. Preventing their use as predictors is a code-audited
research requirement, not enforced blinding. Related ancestral structures and
formulas can cross a material split; inspect the claimed generalization scope.

## Executed worked examples

Use Python3.12, then:

```bash
python3 -m venv /tmp/guo-bench-env
/tmp/guo-bench-env/bin/python -m pip install -r papers/guo-2023-sulfur-xas/requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/guo-mpl /tmp/guo-bench-env/bin/python docs/data/guo-2023-sulfur-xas/workflows/candidate.py ALL --inputs docs/data/guo-2023-sulfur-xas/inputs --output /tmp/guo-answer
```

The candidate computes all observations from the solver inputs. It never reads
the reference averages. Q1 uses two controlled site-treatment ablations and three
Gaussian resolutions. Q2 compares18 combinations of coordination cutoff, shift
observable and confounding control, with material-block uncertainty. Q3 compares
crystal-only, glass-only and hybrid random forests, two resolutions and a majority
baseline, excluding every target-material site from training. These are candidate
choices, not prescribed solutions. Per-question tool-call records are under
`docs/data/guo-2023-sulfur-xas/workflows/Q1.json` (and Q2/Q3).

All worked outputs are under `docs/data/guo-2023-sulfur-xas/verification/Q1/`
(and Q2/Q3). The [execution review](workflow_execution_review.md) records an
independent clean rerun. The [question review](question_quality_review.md) is a
separate adversarial assessment of difficulty, background and task phrasing.

## Verification

```bash
/tmp/guo-bench-env/bin/python docs/data/guo-2023-sulfur-xas/workflows/verify.py --question Q1 --inputs docs/data/guo-2023-sulfur-xas/inputs --output /tmp/guo-answer/Q1
```

Repeat for Q2/Q3. Q1 uses external released averages and permits positive
intensity scaling and one common energy origin. Q2/Q3 independently parse raw
POSCAR and OSZICAR, enumerate periodic neighbors, check submitted identities and
known observations, and reconstruct class metrics. The CLI records declared
cutoffs; nonstandard definitions require corresponding independent review rather
than silently imposing the candidate's labels. Unknown observables receive
finite-value checks and explicit scientific-review flags.

The automatic result is **integrity only**, with `scientific_pass: null`.
The [scientific rubric](../../docs/data/guo-2023-sulfur-xas/verification/scientific_review_rubric.md)
then evaluates design, physical validity, sensitivity, leakage, conclusions and
reproducibility. Baseline predictions can pass arithmetic and still fail the
research task. No accuracy, regression sign or candidate-specific output is a
scientific threshold. The verification audit applies corrupted submissions and
valid alternatives, and checks source packaging independently.

Reproduce the independent verifier audit, including its positive and negative
controls and a full comparison with the extracted releases:

```bash
OPENBLAS_NUM_THREADS=1 /tmp/guo-bench-env/bin/python papers/guo-2023-sulfur-xas/audit_verification.py --candidate /tmp/guo-answer --raw /tmp/guo-raw/22-05-13-LPS-no-POTCAR --reference /tmp/guo-reference/Spectra_66_compounds --release /path/to/release
```

The retained audit accepted 9 valid alternatives and rejected 27 corruptions.
The [scientific assessment](../../docs/data/guo-2023-sulfur-xas/verification/scientific_review.md)
records the worked examples' conclusions and limits separately.

## Rebuild

```bash
tar --warning=no-unknown-keyword -xjf /path/to/22-05-13-LPS-no-POTCAR.tar.bz2 -C /tmp/guo-raw
tar --warning=no-unknown-keyword -xjf /path/to/Spectra_66_compounds.tar.bz2 -C /tmp/guo-reference
/tmp/guo-bench-env/bin/python papers/guo-2023-sulfur-xas/prepare_assets.py --raw /tmp/guo-raw/22-05-13-LPS-no-POTCAR --release /path/to/release --reference /tmp/guo-reference/Spectra_66_compounds
python3 papers/guo-2023-sulfur-xas/build_entry.py
/tmp/guo-bench-env/bin/python papers/guo-2023-sulfur-xas/check_entry.py
python3 scripts/validate_data.py
```

The active dataset gains this paper and a new release ID; previous entries and
their evidence are preserved. Changes are local until separately published.
