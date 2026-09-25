# Evaluator-only rubric for Q5: physical representation discovery

Keep this file, the worked solution, and the target-specific audit out of the solver's input bundle. The scientific question intentionally does not name the representation that motivated this benchmark. Score **scientific quality** separately from **discovery-target attainment**. Until an overall aggregation policy is specified, report both; do not silently convert failure to discover the target into failure of a scientifically valid alternative.

The numerical verifier checks source IDs, declared held-out partitions, paired specimen coverage, phase vocabularies, figures/code/report presence, and submitted numerical evidence finiteness. It independently derives accuracy, F1, confusion counts, and paired errors. It does not infer physical meaning from method names, impose a winning accuracy, judge the research hypothesis, or certify absence of leakage. No solver prediction must match the worked example.

## Scientific validity gates

Trace source labels and all model/representation/interval selections in the submitted code and actual execution. Reading target metadata for scoring is permitted. Using those labels for fitting, prediction, tuning, or selecting a favored model/representation/interval invalidates the affected held-out comparison. Cherry-picking favorable examples to replace the declared evaluation also invalidates that claim. Transparently chosen post-hoc diagnostic failures or illustrative errors are legitimate when the full evaluation is retained. Duplicate or related structural families can also limit independence despite disjoint IDs; assess the claim at the appropriate level.

Every claimed artificial signal must be supported by source-linked saved numerical evidence and executable construction code. Native or merely differently indexed comparisons do not automatically imply signal generation. Determine applicability from the report and code, not from a condition name or the number of named conditions. Missing evidence for a known generated-signal claim leaves the scientific claim unverified even if numerical integrity passes.

False physical claims do not earn discovery credit. For example, relabeling an angular derivative, random projection, or discrete cosine transform as a physical pair-distribution representation does not implement the target. Check the actual axes, units, weights, integration, and interpretation. A hypothesis found ineffective after a sound test remains a valid scientific result. Do not confuse an honest numerical error or weak hypothesis with misconduct; identify which claims are unsupported and why.

## Scientific quality (100 points)

| Dimension | Points | Evidence needed for full credit |
|---|---:|---|
| Physical hypothesis and competing explanations | 25 | A specific hypothesis links scattering/structural information, nuisance sources, and phase-discriminating features. The proposed analysis follows from that hypothesis. Plausible alternatives are considered and tested sufficiently to distinguish mechanism from generic smoothing, model capacity, preprocessing, or a different weighting of peaks. A correct physical alternative can receive full credit. |
| Implementation and physical correctness | 20 | Code and saved numerical probes implement the proposed hypothesis with correct coordinate conversions, units, normalization, sampling, and physically justified approximations. Independently reconstruct representative results directly from source arrays. Document what the chosen representation preserves and loses. |
| Evaluation and independence | 20 | Both supplied chemical systems are evaluated on held-out source records, with tuning/selection kept separate. Comparisons share specimens and report uncertainty appropriate to repeated phases and artificial draws. Conclusions distinguish known-phase augmentation tests from generalization to unseen structures. |
| Mechanistic and quantitative evidence | 25 | Core performance and errors agree with source-derived scoring. Appropriate controls test the proposed explanation, including relevant nuisance behavior and/or weak discriminating features. Examine informative failures and successful cases rather than showing only a favorable aggregate score. Preserve the distinction between representation distortion and actual identification ability. |
| Interpretation and reproducibility | 10 | Runnable code and accessible artifacts reproduce the analysis. Conclusions are proportional to the evidence, cover limitations and alternatives, and report negative findings faithfully. Uncertainty over a small fixed panel is not presented as universal certainty. |

Assign evidence-based partial credit within each dimension, state the validity-gate outcome, and identify unverified claims. Low absolute accuracy is not an automatic scientific failure. A method that performs well through leaked labels, arbitrary target restriction, or unsupported physical claims does not pass the validity gate.

## Target-method evidence scale (0–4, reported separately from exposure)

The evaluator's specific technical target is proposing and testing a **virtual pair-distribution representation** of the available diffraction pattern: convert recorded two-theta to reciprocal magnitude using the supplied wavelength,

`Q = 4π sin(two_theta / 2) / λ`,

and construct a real-space signal through a physically consistent finite-range sine transform of Q-weighted intensity, for example

`G(r) = (2/π) ∫ Q I(Q) sin(Qr) dQ`.

Equivalent properly derived conventions are admissible. Account for radians versus degrees, reciprocal-space integration weights, finite support, distance units, and preprocessing. An uncorrected transform of these released intensity patterns must not be represented as a fully corrected, quantitatively normalized total-scattering PDF. No particular distance grid, interval, classifier, split fraction, normalization recipe, or fusion rule is required.

| Stage | Evidence |
|---|---|
| **0 — not demonstrated** | Target is absent, appears only as a keyword/citation, is asserted without a physical derivation, or the claimed implementation actually performs another operation. A well-supported alternative may still have a high scientific-quality score. |
| **1 — physically proposed** | The report derives or clearly motivates the reciprocal-space to real-space representation, including Q weighting and scattering/structural interpretation. An unimplemented proposal stops here. |
| **2 — correctly implemented** | Runnable code and independent raw-to-derived numerical checks establish the physical operation and its units/convention. Mentioning a library or renaming a variable is insufficient. Implementation alone does not establish identification benefit. |
| **3 — tested without selection leakage** | Stage 2 plus a valid held-out identification comparison against an appropriate baseline, with selection kept out of the test data, paired specimen evidence, and uncertainty. A lower score than the baseline can still meet this stage. |
| **4 — mechanism tested** | Stage 3 plus discriminating validation of the physical explanation: source-linked artifact localization, nuisance suppression and retained phase information, weak-feature/near-confusable-phase evidence, or comparably direct tests with suitable competing controls. Numerical perturbation energy alone is insufficient. The investigation must connect the derived representation to actual held-out discrimination and discuss alternatives. |

Stage 4 establishes **technical method evidence**, not independent discovery by itself. A valid negative finding can supply full technical evidence. If a solver implements and tests a different physically justified representation, report its scientific score, the evidence for that representation, and technical stage 0 without alleging an incorrect scientific answer.

Record target exposure separately: `known-target` (evaluator/worked-example author already knew the target), `target-withheld-in-recorded-run` (an audited isolated bundle/run withheld the target-specific material), or `unknown`. The known-target worked candidate is **ineligible for a claim of unassisted discovery**, even if its technical method evidence reaches stage 4. Report its independent discovery as not assessed/not demonstrated. For an eligible target-withheld run, benchmark target attainment requires stage 4 plus no observed target exposure in the recorded run. Unknown exposure does not establish independent discovery. An isolated run cannot prove that a model lacked relevant prior knowledge or establish historical novelty; report the observed evaluation conditions, not invented novelty.

## Required review procedure

1. Inspect the recorded hypothesis and its code implementation; distinguish pre-evaluation choices from explanations added after seeing outcomes. Assess whether the submission actually supplies evidence of discovery. Retrospective prose alone cannot prove the chronological discovery process.
2. Audit source data and target-label dependencies. Rerun in an isolated bundle containing only the prompt and released input projections. Inspect tuning/selection paths as well as declared split tables.
3. Independently recompute numerical performance and selected physical intermediates. Reconstruct source-linked generated signals when they are claimed. Inspect figures and check that captions and conclusions match the saved evidence.
4. Consider competing explanations and controls. Reward evidence against a favored hypothesis when it is honestly obtained. Assign the scientific score and target stage separately, with reasons and unresolved limitations.

## Calibration cases and verification-loop boundaries

The discovery audit includes numerical controls with free method names, consistent lower-accuracy alternatives, and correct source-derived metrics. These must pass numerical integrity. It also includes deliberately unsupported physical claims, label-copying source code, and missing evidence for a known perturbation experiment. Such fixtures may pass numerical integrity when their declared tables are consistent; their explicit scientific/code review must reject the corresponding claims. This demonstrates a limitation rather than concealing it behind an automated “correctness” verdict.

Actual independently implemented physical alternatives should be reviewed on their own merits. Synthetic renamed/altered prediction fixtures are only tests of the verifier's neutrality; they are not evidence that an alternative scientific workflow has been executed. Record this distinction in audit reports.
