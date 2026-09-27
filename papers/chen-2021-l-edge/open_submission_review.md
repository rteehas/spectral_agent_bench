# Independent review of open-submission verification

Verdict: **pass for its explicitly partial integrity-routing scope**. The open checker does not award scientific acceptance, validate an unspecified geometry definition, or make the worked workflow's analysis choices mandatory. It returns `scientific_pass: null` and identifies the remaining numerical, code-execution and scientific reviews. The detailed worked-profile checker is appropriate only when a submission declares matching conventions.

The reviewer inspected `workflows/verify_submission.py` and independently executed ten controls through `papers/chen-2021-l-edge/audit_open_independent.py`. The retained results are `verification/open_submission_independent_controls.json`; final source hashes and the review scope are in `verification/open_submission_independent_review.json`.

| Control | Expected and observed route |
|---|---|
| Arbitrary learner/split names, only public prediction and partition columns, alternative recognized observation/label column names | Integrity pass, scientific review still required |
| `training` and `holdout` role aliases | Integrity pass, scientific review still required |
| Unknown native prediction identity | Integrity failure |
| Unknown native observation identity | Integrity failure |
| Same-composition polymorph moved into training while another remains in test | Integrity failure |
| Same-composition polymorph moved into validation while another remains in test | Integrity failure |
| `nan` prediction label | Integrity failure |
| Custom partition material alias | Identifier mapping pending |
| A custom material alias used consistently in observations, predictions and partitions | Identifier mapping pending |
| Unrecognized declared partition-role vocabulary | Vocabulary mapping pending |

The two accepted interface variants retain the candidate predictions; this tests freedom of output naming and schema, not independent training of a different learner. The leakage controls use different actual material identifiers sharing a reduced composition, so rejection cannot be attributed merely to duplicate material rows. Training and validation contamination are tested separately.

Adversarial review exposed three issues in the initial generic checker. Nonfinite prediction strings were accepted, common role aliases were rejected despite no public role enum, and custom/resolved identifiers could be rejected before reaching the unresolved-mapping route. These were fixed and independently rerun. Unknown aliases now produce `integrity_pass: null` and `numerical_validation: pending_identifier_or_vocabulary_mapping`, with an explicit obligation to establish the native record/structure mapping. A pending representation is neither an accepted scientific result nor proof of a scientific error.

For known source conventions, identity and composition-partition checks have concrete native anchors. For other valid scientific choices, the checker deliberately routes geometry, spectral-weight definitions, site populations, reconstruction, modeling and claim assessment to independent review. Scores against submitted labels are explicitly arithmetic against those labels, not independent confirmation of geometric truth. A plausible output table, or even a passed integrity screen, cannot establish spectra-only modeling, complete evaluation populations, fair edge comparisons or evidence for the narrative claim. Those remain mandatory acceptance work rather than implicit automatic passes.
