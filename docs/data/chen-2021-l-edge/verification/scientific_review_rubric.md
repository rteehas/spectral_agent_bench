# Scientific acceptance is separate from numerical integrity

`verify.py` returns `scientific_pass: null` even when every numerical check passes.
The evaluator must inspect the submitted code, execute it from the packaged native
records, and judge the following scientific criteria. A command printed in a
report is not evidence of successful reproduction. No archived score, effect
direction, particular geometry algorithm, or plotting style is an acceptance
target. The supplied candidate is a runnable example, not the unique answer.

## Common requirements

- State the population actually studied. The package contains all Ti–Cu records
  from the release, not its entire element range. Account for unpaired edges,
  negative intensities, inconsistent structures and incomplete site coverage.
  Demonstrate that a filtering rule is scientifically justified and does not
  select examples by their desired outcomes. Numerical coverage alone does not
  establish representative chemistry.
- Recover every structural target from the supplied structures. In particular,
  coordination four does not by itself establish tetrahedral geometry, and
  coordination six does not by itself establish octahedral geometry. Show that
  the local-environment rule distinguishes these arrangements and exposes
  distorted or ambiguous cases. Check periodic neighbors, cutoffs and sensitivity.
- Keep the distinction between simulated FEFF spectra and experimental spectra.
  This release does not support claims of experimental predictive accuracy or
  causal attribution of a spectral difference to a single physical variable.
- Inspect exclusions, uncertainty, fitted transformations, comparisons and
  narrative claims, rather than accepting a collection of plausible plots.
  Require sufficient support for every subgroup on which a conclusion depends.
- Unsupported conventions in the numerical checker are review obligations,
  not automatic rejection. Reconstruct those calculations independently before
  accepting them. Conversely, a supported convention is not automatically sound
  for every scientific interpretation.

## Q1: Site populations, edge fingerprints and resolution

- Reconstruct crystallographic equivalence and absorber multiplicities from the
  actual unit cell, checking their stability where symmetry tolerances matter.
  Representatives must cover each required equivalence class exactly once for
  an asserted complete average. Missing or invalid records must not silently
  acquire weight through renormalization.
- Require complete-population fingerprints and meaningful comparisons against
  site simplifications. Distinguish loss of site information from artifacts of
  grid interpolation, support truncation, edge alignment or normalization.
  Compare both the size and distribution of distortions, including chemically
  interpretable examples and cases in which simplification has little effect.
- Evaluate both L2 and L3 fingerprints and state their energy supports. A
  physically placed sum is an optional further representation; if used, explain
  missing energy support and any interpolation/extrapolation. An extrapolation
  convention is not a ground-truth observable.
- Resolution comparisons must implement a stated physical energy broadening
  consistently across conditions and assess at least two resolvable scales.
  Verify any claimed change in distortion rather than relying on one selected
  picture or expecting broadening necessarily to improve every error measure.

## Q2: Geometry and edge weight

- The edge-weight estimator must use the native intensities without a separate
  arbitrary renormalization that destroys their relative scale. Check energy
  reference, background, integration support, and negative/zero denominators.
- Establish the geometry association with uncertainty and adequate class support.
  Assess chemistry confounding using at least absorber identity and meaningful
  ligand/composition information. Report lack of overlap or sparse categories;
  a pooled difference can be dominated by chemistry or by one abundant family.
- Assess robustness to reasonable environment and spectral-weight definitions.
  One threshold or one convenient integration window does not settle a general
  statement. A null or reversed association is acceptable if supported.
- FEFF edge-weight associations alone cannot establish a spin state, oxidation
  state, orbital occupancy or causal effect of geometry. Discuss these limits
  when interpreting a putative branching ratio.

## Q3: Information added by L2

- Derive all targets from structure alone and all predictive features from
  spectra alone. Material IDs, formulas, absorbing species inferred from a
  filename, geometry labels and bond lengths must not enter spectral predictors.
  Absolute photon energy can itself reveal chemistry; explain what the chosen
  reference retains and what it removes.
- Keep all polymorphs, site representatives and both edges for the same reduced
  composition on the same side of an evaluation partition. Inspect training
  code to rule out leakage from fitting transforms, tuning, selection, balancing
  or choosing the experiment after viewing held-out outcomes. A valid partition
  file cannot prove that a model used those partitions.
- Compare L3 and L2+L3 on the same held-out specimens with a justified baseline
  and comparable training effort. Include relevant minority-class evidence and
  composition-aware uncertainty in their paired difference. Do not impose a
  minimum accuracy or assume adding L2 must help.
- Check how many distinct compositions and examples support the result, whether
  geometric exclusions restrict the claim, and whether the conclusion concerns
  the tested learner or information absent from spectra in principle. One
  learner's negative result does not prove that L2 carries no additional signal.

## Evidence record

Retain the executed command, environment, output locations, numerical report,
claim-by-claim review and any unresolved limitations. A scientific verdict must
name the particular candidate and evidence reviewed. Difficulty claims require
separate empirical evaluation of competing systems; a successful worked run and
adversarial corruption tests establish executability and evaluator sensitivity,
not a measured benchmark difficulty level.
