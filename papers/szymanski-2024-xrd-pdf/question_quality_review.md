# Independent question-quality review: open research revision

Verdict: **pass on scientific task design**, with the evaluation-boundary limitation below. This review replaces the earlier approval of prescribed ridge/template experiments. It assesses the standalone solver prompts and raw-data packaging, independently of the worked implementation.

## What changed

The solver receives raw numeric spectra, label tables, and one inline prompt. The former protocol, output-schema, and background README inputs are removed. The prompts define neither preprocessing nor angular truncation, training proportions, estimator families, hyperparameters, score combination, perturbation distributions, severities, or distance windows. Those decisions now belong to the solver. There is no expected numerical outcome or preferred representation in the prompts.

The output contract describes reviewable evidence: record-level predictions, source-record partitions, recomputable metrics, figures, runnable code, and a scientific report. It does not force agreement with the candidate implementation. The fields distinguishing method, representation, condition, and fold support comparison of genuinely different scientific designs. Q3 additionally needs saved perturbation evidence because the solver creates part of its experiment.

## Question-level assessment

| Question | Distinct scientific problem | Why it requires substantial work |
|---|---|---|
| Q1 | Reliability of representation and combined evidence | Requires a defensible supervised evaluation, meaningful sensitivity to analysis choices, paired failures, uncertainty, and a qualified comparative conclusion. Model selection and information combination are left open. |
| Q2 | Constituent identification and unknown cardinality | Requires inference of both labels and count from overlapping signals using single-phase information, calibration without released mixture labels, and failure analysis across mixture complexity. No oracle count is supplied to inference. |
| Q3 | Robustness versus phase discrimination | Requires designing perturbations and intervals, controlling source-record leakage, selecting an interval independently of its final evaluation, and demonstrating classification performance rather than substituting retained signal energy. |
| Q4 | Transfer to measured spectra and secondary-phase evidence | Requires reconciling simulation/measurement differences, searching the full chemistry library, evaluating missed and spurious formulas, and assessing abundance-dependent evidence with dependence and limited sample size in mind. |

These questions overlap in physical representations but concern separate research stages: single-phase representation reliability, mixture identifiability, representation robustness, and experimental transfer. None requires another question's solution. Their difficulty comes from scientific design and evidence synthesis rather than adding prescribed processing steps. Difficulty has not been calibrated by a distribution of independent solver success rates.

## Necessary context and neutrality

The inline background gives native array layouts, angle units, phase-label meaning, augmented-repeat meaning, wavelength, and the mathematical meaning of an uncorrected virtual PDF. These are necessary to interpret the supplied arrays and avoid silently substituting a normalized total-scattering PDF. Task-specific background explains experimental formula-level labels, preparation abundances, or already-present simulation artifacts only where needed. There is no publication reference, figure number, historical score, source conclusion, preferred model, or answer-bearing window range in the solver prompt.

The output section is longer than the scientific question because it makes numerical claims auditable. Those formatting requirements do not tell a solver how to solve the physical problem. Specifying held-out evaluation, forbidding target-label use, and preserving source-record separation are scientific validity requirements rather than a worked recipe.

## Input and verification boundary

Q2 pools two- and three-phase arrays under opaque IDs and removes phase-count-bearing source paths and predefined splits. Q4 supplies the full same-chemistry simulated library rather than a four-formula candidate shortlist. No fitted models, transformed spectra, expected predictions, candidate implementation, or evaluator outputs are included in exports.

**The label tables remain readable.** These are autonomous scientific-analysis tasks with evaluation labels, not access-controlled blind prediction competitions. A solver could violate the instruction by reading target labels during tuning or inference. Numerical output checks cannot establish absence of that leakage; source-code and execution review remain necessary. The same limitation applies to unknown-cardinality inference because label-list lengths reveal count if improperly consumed.

Verification should accept supported null or negative findings and alternative valid methods. It must recompute metrics from released labels and inspect partition/evidence integrity, while assessing scientific conclusions through the separate rubric. Matching the worked answer's estimator, fusion rule, prediction values, preferred interval, or ranking would invalidate the method freedom established by these prompts.
