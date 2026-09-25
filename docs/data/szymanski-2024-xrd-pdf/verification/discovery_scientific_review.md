# Scientific review of the Q5 worked investigation

**Scientific quality: 91/100. Technical target-method evidence: stage 4/4. Independent discovery: not demonstrated; the author knew the target.**

These judgments are separate. This candidate is a reproducible worked investigation with a correct physical implementation and mechanistic tests. It is ineligible as evidence of unassisted discovery and is not a numerical answer key for future solvers.

- **Physical hypothesis and competing explanations: 23/25.** The report links intense versus weak diffraction features and slowly varying contamination to testable alternatives. Signed compression, background subtraction, derivatives, and distance intervals share a classifier family. The weak-feature intervention is honestly distinguished from proof of excessive reliance; the hypothesis and controls were chosen by a target-aware author.
- **Implementation and physical correctness: 19/20.** The Q conversion, reciprocal-space quadrature and uncorrected sine transform are physically stated and independently reproduced. Raw-source preprocessing, generated perturbations, masks and ablation decisions agree with an independent numerical implementation. Angular truncation and fixed nuisance shapes remain deliberate approximations.
- **Evaluation and independence: 18/20.** Both chemistries use disjoint training/validation/test source IDs; model and interval choices use validation conditions only. All alternatives share test specimens. Paired phase-block uncertainty accounts for repeated test phases, but not retraining or selection variability; held-out augmentations are not unseen structures.
- **Mechanistic and quantitative evidence: 22/25.** Strong/weak/random channel ablations, close training-phase pairs, validation artifact localization and actual held-out classification connect mechanism with function. The effective background-subtraction competitor is retained and its paired differences include zero. Only two artificial nuisance families and severities are tested, and mechanistic error analysis is limited to selected phase pairs.
- **Interpretation and reproducibility: 9/10.** The target-aware authorship, weak support for compression, lack of superiority to a simpler competitor, and sampling limits are explicit. The independent rerun matches all deterministic artifacts. Method claims are scoped to this constructed panel; the run does not establish independent discovery or historical novelty.

The validity review found no test-label use in fitting or selection. Transparently reported post-hoc errors were retained alongside the full evaluation. Independently reconstructed source spectra, generated perturbations, quadrature, feature deletion and validation scores support the physical claims. The separate execution review reproduced all deterministic artifacts.

The selected transform interval improved accuracy relative to untreated intensities under the constructed smooth backgrounds. Its uncertainty intervals against background subtraction include zero in both chemical systems. The report handles that competing explanation correctly and does not claim unique or universal superiority.

The automated integrity checker cannot certify discovery, honest label separation, or physical correctness. Deliberate label-copying and false-physical-claim fixtures demonstrate why code and scientific review are required. A different physically justified method can receive scientific credit while the specific technical target is absent.

Target-aware authorship is explicitly disclosed. A future target-withheld isolated run may be assessed for benchmark target attainment, but neither that setup nor retrospective reasoning proves historical novelty or absence of prior model knowledge.
