# Chen 2021: transition-metal L-edge research questions

Three independent questions use native site calculations and periodic structures
from the open L-edge XANES release. Solvers receive raw records, brief format
context and a research question. They receive no processing protocol, geometric
labels, expected trend, reference prediction or worked code.

| Task | Research question | Decisions left to the solver |
|---|---|---|
| Q1 | When do simplified treatments of inequivalent sites distort material L-edge fingerprints? | Establish complete site coverage and populations, reconstruct physical responses, design simplification comparisons and assess resolution dependence. |
| Q2 | Does local geometry predict the balance of L3 and L2 spectral weight after accounting for chemistry? | Define geometric environments and spectral observables, establish chemical overlap, control confounding, quantify uncertainty and assess interpretation. |
| Q3 | Does L2 add coordination information beyond L3 on unseen compositions? | Derive defensible labels, construct matched predictors and controls, design composition transfer and assess chemistry/resolution dependence. |

The questions derive from aggregation, structural interpretation and proposed
inference uses in [Chen et al., Scientific Data 8, 153 (2021)](https://doi.org/10.1038/s41597-021-00936-5).
The sensitivity and transfer experiments are new analyses of the release, not
claimed reproductions of historical numerical results. They are designed to be
difficult research tasks; difficulty has not been calibrated on a population of
scientific agent systems.

## Source data and scope

[Figshare version 1](https://doi.org/10.6084/m9.figshare.12824513.v1), credited to
Yiming Chen (2020), supplies one `L-XAS.json.tgz` archive under an MIT license.
It is 218,348,880 bytes, SHA256
`39d25a0e8085af41d3f0a06bbab0b0e1a8a91968aa21bef23a2397774ccf9537`.
Its single member is newline-delimited JSON despite its `.json` extension.
The independently audited release contains 151,140 records for 22,879 material
identifiers and 69 absorbing elements. There are 53 negative-intensity records
and 1,508 records lacking their partner edge. These exact release counts need
not equal rounded historical descriptions.

This entry retains **all 27,570 Ti, V, Cr, Mn, Fe, Co, Ni and Cu records**, covering
7,618 material identifiers. The eight gzip files total approximately 37 MB.
Each record preserves its original bytes: two native numeric arrays, structure,
absorbing index, identity and FEFF parameters. No selection depends on geometry,
completeness, intensity validity or a predicted target. Negative spectra and
orphan edges remain for the solver to assess. “Raw” denotes the earliest
released numerical calculation data, not experimental detector counts or FEFF
intermediate output. [Provenance](../../docs/data/chen-2021-l-edge/provenance.json)
records both native-stream and packaged hashes.

There are 8,160 material/element identities but only 16,178 observed edge groups:
142 whole L2 or L3 groups are absent. The worked Q1 excludes 386 *observed*
groups and reconstructs 15,792 complete responses. Its exclusion count does not
include wholly absent groups; missing edges are never reconstructed as zero.

The records require actual identity checks: `mp-12905` aliases two physically
different structures in this release. Six other material identifiers have
dictionary differences despite unchanged lattice and coordinates. The candidate
excludes the physical collision and does not mistake optional metadata for a
geometry change. This information is evaluator evidence; the exported inputs
retain the native records.

The release **does not contain** radius/core-hole sweeps, experimental reference
arrays, OCEAN results, author-generated material averages, historical geometry
labels, figure-generation scripts or trained-model outputs. Those missing stages
are not benchmark questions. The [source map](../../docs/data/chen-2021-l-edge/verification/source_map.json)
separates raw truth, benchmark choices and unavailable historical evidence.

The paper points to general open-source packages for workflow code. The review
entry's code link is an inspected
[pymatgen v2020.12.31 spectrum module](https://github.com/materialsproject/pymatgen/blob/v2020.12.31/pymatgen/analysis/xas/spectrum.py),
not an asserted author analysis repository or exact historical commit. That
implementation uses cubic interpolation and extrapolates L2 while stitching a
combined edge. The candidate instead investigates material-averaged L2 and L3
separately on finite native support. It does not claim pixel agreement with the
paper's stitched plots. No FEFF executable or Materials Project API is required.

## Solver boundary

From the repository root:

```bash
python3 papers/chen-2021-l-edge/export_agent_bundle.py Q1 --output /tmp/chen-Q1-agent
```

Replace Q1 with Q2 or Q3. Each export contains only `task.json` and eight native
input files. Attribution and license are retained. There is no separate protocol
or output-schema document. Output identifiers enable independent checks; the
solver chooses the scientific methods.

Use the exported directory in a fresh isolated solver context. Keep the paper,
public review site, source code, candidate, derived labels and evaluator evidence
outside that context; disable external retrieval for the unassisted track. The
exporter does not enforce filesystem or network isolation, and the public site
does not provide access control. Attribution may reveal the source and prior
model knowledge cannot be excluded.

Q3 structures remain available to derive reference environments and conduct
evaluation. Their exclusion from spectral prediction is a code-audited research
requirement, not enforced label blinding. Inspect feature generation, model
selection and partitioning; an output table alone cannot establish absence of
leakage.

## Worked candidate

Use Python 3.12. The exact observed dependency set is also retained in
`requirements-lock.txt`.

```bash
python3 -m venv /tmp/chen-bench-env
/tmp/chen-bench-env/bin/python -m pip install -r papers/chen-2021-l-edge/requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/chen-mpl /tmp/chen-bench-env/bin/python docs/data/chen-2021-l-edge/workflows/candidate.py all --inputs docs/data/chen-2021-l-edge/inputs --output /tmp/chen-answer
```

For one question, use Q1, Q2 or Q3 instead of `all`; its output argument then names
the question directory itself. Each question can run directly from its own
export without another task's answers. The per-question workflow JSON records
tool calls and choices; `verification/Qn/` retains the executed artifacts.

The candidate uses crystallographic populations and complete-coverage checks for
Q1, independent angular/radial geometry and conditional edge-area contrasts for
Q2, and matched composition-held-out spectral classifiers for Q3. Its tolerances,
integration windows, preprocessing, learners and bootstrap design are examples,
not prescribed solver methods. Reports state support, exclusions and limitations.
Computed finite-window edge areas are not experimental white-line branching
ratios or direct evidence of spin state.

The [adversarial question review](question_quality_review.md) checks the exact
prompts and native input boundary. The
[independent execution review](workflow_execution_review.md) reproduces all 34
outputs byte for byte. The
[open-verifier review](open_submission_review.md) independently tests alternative
interfaces, corruptions and unresolved identifier mappings. The
[scientific assessment](../../docs/data/chen-2021-l-edge/verification/scientific_review.md)
evaluates actual claims and their limits. All review artifacts are evaluator-only.

## Verification

```bash
/tmp/chen-bench-env/bin/python docs/data/chen-2021-l-edge/workflows/verify.py --question Q1 --inputs docs/data/chen-2021-l-edge/inputs --output /tmp/chen-answer/Q1
```

Repeat for Q2 and Q3. This is the **worked-example profile audit**: it derives
truth from native spectra and structures without importing the candidate, and
checks the particular declared populations, interpolation, geometry, observables,
partitions and arithmetic. Its additional files and numerical conventions are
not hidden requirements for alternative answers.

For an independently designed submission, use:

```bash
/tmp/chen-bench-env/bin/python docs/data/chen-2021-l-edge/workflows/verify_submission.py --question Q3 --inputs docs/data/chen-2021-l-edge/inputs --output /path/to/submission
```

This separate checker accepts freely named methods and the compact public output
contract. It checks native identities, finite arrays, declared populations where
recognized, and development/test composition exclusion. It explicitly reports
**partial numerical validation** and lists unresolved independent review work.
Any prediction metrics against submitted labels are labeled arithmetic-only
until those labels are independently reconstructed. The evaluator must validate
the solver's own geometric/spectral definitions and execute its code; a surface
pass does not validate its quantities or conclusions. A different interpolation,
label definition, learner, partition or uncertainty analysis is not rejected
merely for differing from the worked example.

Custom material identities or unfamiliar role vocabularies that cannot yet be
mapped return a pending result (`integrity_pass: null`, exit status 2), with an
explicit mapping obligation. This includes valid ways of resolving the native
material-identifier collision. Common training/holdout role synonyms are accepted.

The automatic verdict is **numerical integrity only**, with scientific acceptance
assessed separately using the
[scientific rubric](../../docs/data/chen-2021-l-edge/verification/scientific_review_rubric.md).
The scientific review checks physical validity, nontrivial evidence, chemistry
and dependence controls, sensitivity, uncertainty, leakage and justified claims.
A constant predictor can have correct arithmetic and still fail the research
question. No coefficient sign, positive improvement or minimum prediction score
is required. Code and evidence are necessary for acceptance.

The applied audit checks byte-level source fidelity, accepts valid alternative
submissions and rejects targeted corruptions. Its retained record states which
checks are complete and which require scientific judgment. Original released
arrays and periodic structures anchor verification; no author-supplied averaged
spectrum or label set is invented.

Reproduce the audits from the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/chen-bench-env/bin/python papers/chen-2021-l-edge/audit_verification.py --candidate docs/data/chen-2021-l-edge/verification --raw-source /tmp/chen2021/raw/L_XAS.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/chen-bench-env/bin/python papers/chen-2021-l-edge/audit_open_submission.py --candidate docs/data/chen-2021-l-edge/verification
/tmp/chen-bench-env/bin/python papers/chen-2021-l-edge/independent_replay.py --work /tmp/chen-replay-new --reference docs/data/chen-2021-l-edge/verification --record /tmp/chen-replay-new.json
```

## Rebuild

```bash
python3 papers/chen-2021-l-edge/acquire_release.py --output /tmp/chen2021
python3 papers/chen-2021-l-edge/prepare_assets.py --raw /tmp/chen2021/raw/L_XAS.json --archive /tmp/chen2021/L-XAS.json.tgz --metadata /tmp/chen2021/figshare.json
python3 papers/chen-2021-l-edge/build_entry.py
python3 papers/chen-2021-l-edge/check_entry.py
python3 scripts/validate_data.py
```

Rebuilding the index requires the executed workflows and independent review
records already present. Acquisition verifies the exact versioned archive; the
packaging script copies native lines and never computes solver-facing labels.
The new paper is added to the active local index with a new dataset release ID;
previous papers are preserved. Website publication is a separate action.
