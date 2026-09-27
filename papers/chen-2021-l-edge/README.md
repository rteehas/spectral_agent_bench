# Chen 2021: mandatory verification against publication results

This revision replaces the three extension experiments with two standalone
research questions grounded in results actually plotted by
[Chen et al. (2021)](https://doi.org/10.1038/s41597-021-00936-5).
The publication is the answer key. A plausible new analysis, correct source
identities, or agreement with our worked solution cannot replace agreement with
its results.

| Question | Publication target | Status |
|---|---|---|
| R1: Which spectral features distinguish spinel MgMn2O4 and olivine LiFePO4? | Original FEFF vector curves in Figure 4(c,d), including complete visible shapes and secondary peaks | Paper verified, with independent raw-data replay |
| R2: How do coordination and absorber identity shape Ti–Cu spectra? | All eight Figure 5 panels, both coordination colors, full line-shape and outlier evidence | Unvalidated; withheld from scoring until every mandatory comparison passes |

R1 is a narrower reconstruction task than originally intended. Its difficulty
has not been calibrated on agent systems. R2 requires a substantial structural
and spectral investigation, but computational difficulty does not excuse an
unresolved verification failure. Consult the recorded
[R1 acceptance](../../docs/data/chen-2021-l-edge/paper_results/verification/R1_acceptance.json)
and [R2 acceptance](../../docs/data/chen-2021-l-edge/paper_results/verification/R2_acceptance.json)
for the actual gate results.

## Solver inputs

The eight inputs preserve all 27,570 Ti–Cu native calculation records byte for
byte from [Figshare version 1](https://doi.org/10.6084/m9.figshare.12824513.v1).
They contain separate-edge spectra, periodic structures, source identities and
FEFF settings. Negative spectra, orphan edges and identity collisions are
retained. “Raw” means the earliest released numerical calculation data, not
experimental detector counts. The release is attributed to Yiming Chen (2020)
and licensed under MIT; archive and native-stream hashes are in
[provenance.json](../../docs/data/chen-2021-l-edge/provenance.json).

```bash
python3 papers/chen-2021-l-edge/export_agent_bundle.py R1 --output /tmp/chen-R1-agent
```

Only `task.json` and eight native gzip files are exported. Questions include
minimal field semantics and output formats, without paper references, expected
trends, processing recipes, geometry labels or worked code. R2 export requires
`--allow-unvalidated` for evaluator development and does not grant scoring
eligibility. Use an isolated solver context without the public review site,
paper, candidate code or evaluator assets; the exporter itself does not enforce
filesystem/network isolation.

## Verification

The final acceptance rule is a conjunction of four independently auditable gates:

1. **Publication agreement.** R1 compares against original PDF vector coordinates,
   calibrated from printed ticks, rather than newly calculated reference curves.
   Both panels must satisfy RMSE ≤ 0.02, maximum absolute residual ≤ 0.07,
   L2-height error ≤ 0.05, and an L2-position tolerance determined from source
   stroke width. One rigid L3 registration and global maximum normalization are
   allowed. Missing endpoints, local energy warping and independently rescaled
   edges cannot pass. R2 uses the original raster on calibrated axes; every
   element/color comparison is mandatory. Overplot opacity is never treated as
   an empirical density, quantile or population count.
2. **Independent native-data execution.** A separate agent exports a clean
   bundle, inspects the source, reruns the supplied program and checks every
   produced file. Approval is bound to the eight native input hashes and the
   complete output manifest. The final R1 and R2 candidate outputs were both
   reproduced byte for byte.
3. **Scientific review.** A separate review compares complete plots directly to
   the paper, checks interpretation and records limitations. The review is bound
   to output and publication-target hashes. Qualitative resemblance cannot waive
   a failed mandatory numerical/plot gate.
4. **Verification-loop audit.** Another agent applies positive and negative
   controls and checks the verifier and target hashes. Missing curves, incorrect
   peaks, missing colors, stale reviews, altered native inputs and modified
   artifacts are tested. These checks do not replace the publication comparison.

`check_acceptance.py` reruns the paper comparator and requires all gates. It
returns a failing exit status for missing, false or stale evidence. Reviewer
files are evaluator-owned; a solver cannot approve its own submission.

Complete tool calls, commands and outputs are recorded in
[R1 workflow](../../docs/data/chen-2021-l-edge/paper_results/workflows/R1.json) and
[R2 workflow](../../docs/data/chen-2021-l-edge/paper_results/workflows/R2.json).
The worked methods are evaluator-only. Install the direct dependencies with
`python -m pip install -r papers/chen-2021-l-edge/requirements.txt` in Python 3.12;
`requirements-lock.txt` records the full observed environment.

The paper-target extraction, native-release scope audit, independent reviews,
mutation controls and failed comparisons are retained under
[`paper_results/verification`](../../docs/data/chen-2021-l-edge/paper_results/verification).
The paper figures are CC BY 4.0 with source attribution and extraction provenance.

## What can and cannot be reproduced

Four of the six exact Figure 4 material IDs are absent from the full release.
MgMn2O4 uses the exact released/published `mp-32006` calculation. The released
olivine LiFePO4 `mp-761468` reproduces the plotted curve, but Table 2 names the
absent `mp-19017`; matching a phase response does not prove identical historical
calculation identity. Other tested substitutions and released Pt did not pass
the unchanged Figure 4 tolerances. Their failures remain documented; this entry
claims only Figure 4(c,d), not the whole figure.

The release's exact element counts also disagree with 62 of 69 literal Figure 2
site-wise counts. We do not make those integers agree by changing their
tolerance. Figure 3's radius/core-hole sweeps and experimental reference arrays
are absent. These stages are excluded from validated tasks. Figure 5's original
labels and plotting script are also absent; its complete published plot remains
the required target, with rendering uncertainties recorded explicitly.

The previous `CHEN21-Q1/Q2/Q3` extension tasks, their weaker verification paths
and their old reviews are retired. They remain available only in Git history at
commit `63d90dbfce8925e39b0108418c81b5cb77e65265`. New IDs and a new dataset ID
prevent old reviews from being silently reused for these different questions.
