# Independent scientific review of the executed candidate

This review concerns the frozen `candidate.py` with SHA-256
`72e3ffe98d17a5b305bc8f720e8fc0b35639b1b061412c27f9419e06be51b755`
and the retained `verification/Q1`, `Q2`, and `Q3` artifacts. It does not make the
candidate's definitions compulsory for another submission. The open-submission
checker and rubric provide the route for scientifically defensible alternatives.

The review used the executed outputs, source code, native spectra and structures,
independently calculated numerical checks, and the separate clean replay record.
The latter regenerated all 34 files byte for byte from fresh exported inputs.
The three main diagnostic figures were also visually inspected: their curves,
signs, intervals and legends agree with the numerical evidence. The numerical
checker leaves `scientific_pass` unset; this document supplies an additional
claim-level judgement rather than treating that check as scientific acceptance.

## Q1

**Supported within the declared conventions.** The source-based symmetry and
population reconstruction yields 15,792 complete observed edge responses, with
386 observed groups excluded. The meaningful simplification comparisons involve
5,191 multisite edge responses. Equal weights often agree exactly because all
represented populations are equal; the near-zero median is therefore not a
general demonstration that population weights are unnecessary. At 1 eV FWHM,
the 95th-percentile normalized shape errors are 0.06541 for equal weighting and
0.28053 for retaining the first representative, which supports the report's
material-dependent conclusion. The broadening comparison changes the size and
ranking of errors: the representative approximation retains only 35 of the
unbroadened top-50 materials at 1 eV and 31 at 2 eV. Rank comparisons coalesce
numerical zeroes to avoid interpreting roundoff as physical ordering.

The implementation keeps native absolute intensities during population
averaging, interpolates on physical photon energy, and excludes incomplete
equivalence-class coverage before normalizing weights. Its two simplifications
change either weights or the chosen representative while holding other choices
fixed. All raw observations remain in the audit. Source checks independently
reconstruct multiplicities, complete responses, ablations, 31,146 error rows,
resolution rankings and the tolerance sensitivity of symmetry partitions.

The denominator needs care: the 16,178 coverage rows are **observed**
material/element/edge groups. Among 8,160 observed material/element pairs, another
142 edge slots have no source record at all. Those are absent observations,
not additional reconstructed or silently averaged responses. L2 and L3 are
analyzed separately, so this evidence does not assert that every material has
both complete edges. The first-site choice is arbitrary; other choices can
perform differently. The symmetry-tolerance table documents substantial changes
without proving that one tolerance is physically privileged. These limitations
restrict the result but do not invalidate the stated comparison.

## Q2

**Supported as an operational association, with limited composition overlap.**
The 13,589 valid paired sites contain 1,722 nominal tetrahedral, 3,686 octahedral
and 8,181 other environments. Neighbor directions and radial dispersion, rather
than coordination count alone, determine the regular-geometry classes. Direct
periodic image enumeration independently reproduces the neighbor count,
distortion measures, ligand identities and sensitivity labels. A four-neighbor
square-planar environment cannot pass the tetrahedral angular criterion.

The edge observable preserves native relative amplitudes and integrates each
nonuniform grid over matched excess-energy windows. The first archived energy
is only an operational origin. This is a raw-area ratio, not a background-free
experimental white-line or spin-sum-rule quantity. Source integrals, log ratios,
weighted conditional contrasts and material-cluster bootstrap intervals were
independently reconstructed. The interval implementation uses direct weighted
residualized least squares, whereas the candidate uses weighted moment
subtraction; both agree within numerical tolerance.

The element/ligand-adjusted nominal contrast is -0.01201, with interval
[-0.01530, -0.00868], on 4,592 sites in 3,005 materials. It remains negative over
the tested operational choices. Full composition adjustment is much less
informative: only 301 sites in 108 materials support the nominal contrast
-0.01467, with interval [-0.04305, 0.00201]. One tightened-shell composition
interval barely excludes zero; the others do not establish a general
composition-invariant effect. The report explicitly leads with limited overlap,
distinguishes partial adjustment from exact composition control, and avoids
causal, spin-state and oxidation-state claims. The scientific claim is therefore
appropriately narrower than a universal geometry dependence.

## Q3

**Supported for the specified learner and regular-geometry population.**
The comparison uses the same 5,408 sites, 3,602 materials and 3,339 reduced
compositions in four held-out folds. Source-derived formulas independently
confirm that polymorphs of a composition cannot cross a train/test boundary.
The source code constructs spectral-model features solely from intensities and
their energy coordinates. Per-sample normalization does not fit held-out data;
all model fitting and class weighting use training data. There is no tuning or
feature selection using held-out labels. Material/element information is used
for grouping and diagnostics; the element-prior predictor is a separately
identified baseline.

The unbroadened L3 balanced accuracy is 0.95719; L2+L3 gives 0.95936. Their paired
increment is 0.00217 with composition-bootstrap interval [-0.00076, 0.00574].
At 1 eV, the interval for the 0.00143 increment also includes zero. Majority
and training-only element-prior baselines give 0.50000 and 0.68000. Independent
checks recover the actual structural labels, partition memberships, prevalence
predictions, confusion matrices, scores, intervals and paired differences.
The code and independent replay establish that the retained predictions were
actually produced by the declared fitted models; a prediction table alone
could not establish that.

The claims appropriately distinguish failure to resolve an increment from
proof that L2 has no information. Per-element effects have different signs and
small subgroups, notably only 41 tetrahedral Ti examples. Geometry-stability
assessment re-evaluates the same predictions on a stable-label subset; it is
not retraining under alternative labels. Bootstrap intervals condition on the
fitted folds and do not include model-fitting variation. High nominal accuracy
does not establish transfer to experiments, uncertain alignments, new elements
or irregular environments.

## Verification scope and benchmark difficulty

The strict worked-profile audit is deliberately stronger than surface-schema
checks but applies only to this candidate's declared conventions. Actual
positive and corruption-control outcomes are retained under `verification/audit`.
The alternate-grid positive establishes that stored knots are not an answer
key. The coherent zero-increment positive establishes that a particular score
or positive L2 benefit is not required; it is a synthetic numerical control and
is not accepted as a scientific submission. Negative controls exercise invalid
IDs, coverage, finite values, weights, averages, geometry, integrals, effects,
intervals, labels, predictions, metrics and composition leakage.

These investigations require substantive source repair, crystallography,
spectral processing and statistical reasoning. The executed candidate and
adversarial checks establish a viable research benchmark with independently
checkable answers. They do **not** establish empirical difficulty against
scientific multi-agent systems. Difficulty calibration requires separately
measured system performances without evaluator artifacts in their context.
