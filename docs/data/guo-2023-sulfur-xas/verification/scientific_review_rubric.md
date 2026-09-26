# Scientific acceptance

The automatic checker establishes source consistency and submission integrity. Its
`scientific_pass: null` is intentional. A scientific pass requires review of the
submitted analysis code, numerical artifacts, execution record and report. A
matching reference array or arithmetically valid classifier does not suffice.

## Shared requirements

1. **A research answer.** The report answers the stated question with quantitative
   evidence, including negative findings. It does not just reproduce a plot or
   describe what someone else should investigate.
2. **Physical and numerical validity.** Correct absorber identity, periodic
   geometry, excitation-energy reference and multiplicity treatment. The absolute
   DFT axis must not be presented as experimentally calibrated. Interpolation,
   normalization, spectral coverage and broadening choices must be defensible.
3. **Valid scope.** Distinguish 2,681 site calculations from 66 independent
   structures. This selected archive is neither a representative population nor a
   randomized intervention. Explain dependence, imbalance and composition or
   ancestry confounding relevant to the claim.
4. **Sensitivity and uncertainty.** Test the choices that could change the answer.
   Sampling uncertainty must respect material dependence; deterministic complete
   archive comparisons may use numerical/assumption sensitivity instead of
   confidence intervals. State what an interval excludes (for example training
   variability). No required positive result or exact score.
5. **Reproducibility.** Runnable code must regenerate the submitted observations,
   curves and conclusions from task inputs. Check execution rather than trusting
   self-reported aggregate values. Evidence may use different filenames/methods
   where an equivalent independently auditable result is supplied.

## Q1: site treatment and material response

Require complete source-consistent unbroadened material responses and meaningful
counterfactuals that isolate site-energy and site-population assumptions. Preserve
common energy references; arbitrary per-material realignment can erase physical
differences. Show which structures are sensitive and why, and how conclusions
change with justified resolution assumptions. Distinguish relative site alignment
from a common bulk shift and reduced multiplicity ratios from absolute atom counts.
Merely summing supplied averaged spectra, matching one curve or asserting that
broader curves are smoother fails the scientific question. Do not require the
example's grids, cubic interpolator, exact ablations, Gaussian widths, distance
metric or material ranking. The raw released averages are a strong numerical
anchor; the separately broadened/shifted outputs have undocumented additional
calibration and are not an exact benchmark target.

## Q2: coordination and shifts

Require declared and defensible coordination and shift definitions, an analysis
that addresses phosphorus environment and composition/material confounding, and
sensitivity capable of challenging a simple red-shift rule. An unadjusted pooled
correlation or only one hand-picked crystal is inadequate. Check site assignment,
periodicity, spectral feature extraction and regression/association arithmetic.
Material fixed effects are one possible control, not a required estimator.
Consider nonlinearity, minority-environment support and related structure
dependence when judging the strength of conclusions. A negative, weak or
definition-dependent relationship is valid. Do not infer charge redistribution or
electronic shielding causally from coordination correlations alone. There is no
author-reported slope or universal edge definition to match.

## Q3: coordination inference and transfer

Require crystal-trained and glass-informed comparisons on all released glass
structures, without target-material sites in fitting, preprocessing selection or
hyperparameter tuning. Structural coordinates may establish labels but must not
enter prediction; neither identifiers, composition, origin nor multiplicity may
serve as spectral predictors. Inspect code for leakage, not just partition CSVs.

Require class-wise errors and a meaningful baseline: a constant P-coordination1
predictor is about97% accurate on this archive. Arithmetic acceptance of that
baseline does not establish useful inference. Compare rare-class recall and
uncertainty, and investigate resolution sensitivity. Material-held-out results do
not by themselves establish unseen-composition/ancestry transfer, bulk-spectrum
inference or experimental performance. Differences between crystal-only and
glass-informed training also reflect sample size and coverage; avoid attributing
them solely to disorder. Alternative estimators, neighbor definitions, folds and
negative outcomes are acceptable if adequately validated.

## Verdicts

Record each question as `pass`, `needs_revision` or `unsupported`, with evidence
paths and limitations. Do not turn this into a hidden performance threshold or
require agreement with the worked candidate. The supplied candidate is one
feasible answer, authored with knowledge of the source; its reviews do not
calibrate benchmark difficulty on an uninformed population of agents.
