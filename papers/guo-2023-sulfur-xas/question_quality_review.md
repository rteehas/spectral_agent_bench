# Independent adversarial question-quality review

Verdict: **pass** for the final standalone questions, input boundary and research-task design. The machine-readable companion records exact prompt text, reviewed hashes and independently executed export checks. This review does not replace the separate workflow-execution or verification audit.

The three questions ask about distinct research stages: material-spectrum construction, conditional structural interpretation, and inverse local-environment inference. Each has the complete raw release projection and can be answered independently. None asks the solver to reproduce a paper, match a published conclusion or follow a worked protocol.

## Scientific difficulty and neutrality

| Question | Substantial scientific work | What remains open |
|---|---|---|
| Q1 | Recover material responses and establish how site energy and population differences affect fingerprints at finite resolution. Reconstruction alone is insufficient. | Interpolation, resolution model, comparisons, measures of distortion and treatment of exceptions. |
| Q2 | Test the lithium-coordination/red-shift hypothesis while addressing phosphorus bonding, composition, dependent observations and physical interpretation. A pooled correlation is insufficient. | Neighbor and shift definitions, confounding model, uncertainty design and conclusions. |
| Q3 | Establish geometry-derived labels, test crystal-to-glass transfer, compare glass training, and assess uncommon environments and resolution. Aggregate accuracy is insufficient. | Spectral representation, predictor, tuning, partition design beyond target-material exclusion, resolution model and conclusions. |

Q1 is grounded in the database's reconstruction and averaging stage. Q2 examines a physical hypothesis motivating its interpretation. Q3 develops a proposed use of its site spectra. The latter two are new analyses supported by released data, not claimed reproductions of historical regressions or machine-learning results. A null or negative answer remains valid. Asking whether red shifts occur defines a hypothesis; it does not supply its outcome.

## Minimal context and output requests

The common background is 91 words. It describes array columns and units, raw calculation text, absorber identity, site multiplicity and energy-reference conventions. These facts are necessary to interpret the native data. In particular, the energy convention prevents an undocumented discrepancy in the released parsing code from becoming a hidden benchmark rule. No energy-alignment equation, processing algorithm, coordination threshold, estimator, energy window, broadening kernel, score target or expected physical result is given.

The requests for reports, figures, runnable code and numerical observations make the answers reviewable. Q1's energy/intensity arrays support comparison against independent released material outputs. Q2's site identities support raw-geometry and spectral audits. Q3's labels, predictions and material assignments support independent reconstruction of transfer evidence. These compact output contracts do not prescribe the scientific analysis. Requiring exclusion of every target-material site from training or selection defines the intended generalization question rather than a fitting recipe.

Two wording issues were corrected before approval. Q1 no longer asks for inter-material discrimination conclusions unsupported by its worked distortion analysis. Q3 now allows structural information to define labels, including training labels, while keeping predictors spectral. A related checker mismatch was also identified: Q2 permits justified source subsets and Q3 need not report unused crystalline labels. The checker now reports Q2 coverage and requires Q3 glass targets, instead of silently demanding every source row.

## Inputs and isolation

I independently exported all three final tasks. Each export contained exactly nine files: task.json and eight raw-input assets. Exported input hashes matched their source assets and the task text matched the final entry. The six NPZ archives contain 2,681 distinct float64 arrays with four native columns. Calculation JSON contains unchanged neutral/site input-output text for 66 materials. There are no precomputed coordination labels, processed spectra, candidate code, worked answers or evaluator files in these exports.

The spectra are cropped native VASP release records, not detector raw counts or complete original VASP outputs. Material identities and structure origins are legitimate released metadata. Source attribution is retained, so the bundles are not anonymous. Following it online could expose the paper and averaged outputs. The documented runtime must therefore isolate the solver from the review repository and external retrieval; the public review website is not an access-control boundary.

Structures remain readable so the solver can construct labels. Compliance with spectra-only prediction and target-material exclusion needs code and execution review. Numerical output checks cannot establish that compliance by themselves.

## Fair acceptance and scope

Alternative defensible coordination definitions, representations, models, resolutions and conclusions must not fail merely because they differ from the worked example. Exact checks apply to source identity, reconstructable geometry and energies, arithmetic and independently released material responses. Nonstandard descriptors need an appropriate independent audit; scientific adequacy requires the separate rubric. A constant predictor can pass arithmetic while failing the research question.

The 2,681 sites belong to 66 structures. Related ancestral structures and formulas can cross material splits. Q3 therefore concerns unseen released structural models, and its evidence alone does not establish new-chemistry or new-family transfer. The release also cannot establish experimental transfer, computational convergence, charge redistribution or a causal shielding mechanism without additional data. Intended difficulty is supported by the required scientific work but has not been calibrated against a population of solver systems.
