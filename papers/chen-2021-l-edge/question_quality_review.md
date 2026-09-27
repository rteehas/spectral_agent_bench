# Independent adversarial question-quality review

Verdict: **pass** for the standalone question text, scientific scope and solver-input boundary. This review does not certify the worked workflow or replace the independent verification audit. Exact reviewed prompts, hashes and independently executed export/source checks are recorded in `verification/question_quality_review.json`.

The review applied the concise research-task standard used by the validated Guo and Torrisi entries. The initial standalone wording passed the research-task standard. Subsequent source and workflow inspection prompted two narrow corrections: `mp-id` is described as a released identifier rather than a unique crystal, and Q1 explicitly names L2 and L3 fingerprints to match the separate-edge aggregation scope. The reviewer nevertheless raised scientific acceptance issues with the workflow and verification agents before execution: geometric labels cannot be replaced by coordination numbers alone; partial chemistry adjustment cannot establish a geometry effect at fixed composition; numerical reconstruction conventions cannot silently become unique physical truth; and FEFF spectral associations cannot establish spin states.

## Research questions and difficulty

| Task | Substantial scientific work | Decisions left to the solver |
|---|---|---|
| Q1 | Establish when the released site calculations support complete material responses; reconstruct those responses; determine the consequence of simplifying site differences and populations, including finite resolution. | Symmetry analysis, completeness criteria, interpolation and edge combination, simplification comparisons, resolution model and distortion measures. |
| Q2 | Define local geometric environments and spectral weights, assess their association conditional on chemistry, and establish whether plausible definitions change the conclusion. | Neighbor and shape definitions, spectral observable and windows, adjustment or matching design, uncertainty and interpretation. |
| Q3 | Establish structural reference labels, compare L3-only and paired-edge inference for unseen compositions, and assess chemistry and resolution dependence. | Representations, predictors, model selection, partition construction, broadening and uncertainty. |

Q1 concerns a concrete database-construction step. Q2 turns the environment-dependent spectral interpretation into a conditional scientific test. Q3 examines a proposed use of the database through a new paired-edge generalization experiment. These are distinct stages, independently answerable from each task's complete input bundle. The task wording does not claim that the latter analyses reproduce historical author regressions or learning experiments.

A list of counts, a plotted mean spectrum, a pooled geometry correlation or a single classification accuracy cannot settle the respective questions. A defensible negative finding remains valid. The task names identify scientific hypotheses and comparisons without revealing their outcomes.

## Minimal context and freedom of analysis

The common background only identifies the computational spectra and absorbing elements, JSONL container format, spectral units and arrangement, absorber indexing, record/material identifiers, structure coordinates and the retained intensity scale. It does not provide aggregation equations, symmetry tolerances, shape cutoffs, integration windows, spectral alignment procedures, broadening kernels, statistical models, split counts or expected values. No task asks the solver to consult or reproduce a paper, figure, table or released solution.

The output requests make the scientific evidence auditable: material response arrays and contributing populations for Q1, observation-level structural and spectral quantities for Q2, and labels, predictions and partitions for Q3. They contain no processing recipe. Withholding test compositions from model development defines the transfer question rather than supplying a model-fitting protocol.

Native L2 and L3 calculations can be compared through defensible operational spectral-weight definitions. Those definitions must be explained; the raw edge-area ratio is not automatically an experimental white-line branching ratio. Tetrahedral and octahedral labels require geometric support: fourfold coordination alone does not exclude square-planar arrangements. Composition may be used for evaluation assignments and confounding assessment even though it is excluded as a spectral predictor in Q3.

## Independently checked input boundary

The reviewer executed all three task exports. Each contains exactly nine files: `task.json` and the eight native-data gzip files. All exported input hashes match the source assets, and the exported prompt text matches the reviewed questions. No workflow, reference answer, derived geometry label, processed spectrum or verifier is exported.

An independent full scan compared the eight input files against the original `L_XAS.json` member. All 27,570 selected records are byte-identical original lines, with no omitted or added records for the named absorbing elements. All retain the seven native fields: `absorbing_atom`, `edge`, `input parameters`, `mp-id`, `name`, `spectrum` and `structure`. Each native spectrum has two 100-point arrays and a monotonic energy axis. The cohort includes 7,618 distinct released material identifiers, 8,160 material-identifier/element groups and 53 records with negative intensity. These identifier counts are not a claim that each identifier represents exactly one structure. The input selection therefore does not pre-solve validity screening or completeness assessment.

The input spectra are the earliest numeric FEFF results in this release, not detector observations or full FEFF intermediate output. Source attribution remains in the exported task. The public review site and repository expose evaluator material, so a blind evaluation must isolate the exported bundle and prevent access to those references and external retrieval. The export alone is not an access-control mechanism.

## Fair verification and scientific limits

Exact checks can establish native source identity, arithmetic, recoverable structural quantities, and documented reconstruction conventions. They cannot make a particular coordination definition, edge integration window, interpolation method, classifier or prediction score uniquely correct. Alternative justified choices and null findings should remain admissible; an evaluator must assess the resulting claim on its own evidential terms.

Q2 needs explicit attention to what the chosen adjustment actually controls. An element-stratified association or a ligand-family comparison can leave substantial composition confounding. A small or absent set of comparable compositions can justify a limited conclusion rather than a claimed geometry effect. Dependent sites within a material and multiple structures of a composition also affect uncertainty.

Q3 requires genuine composition exclusion throughout model development and a fair paired comparison of information sources. Nominally held-out material IDs alone do not establish unseen-composition transfer. Scientific acceptance also requires evaluating whether an apparent improvement is robust, whether one environment dominates the score and whether the tested chemical population supports the stated generalization.

The final background calls `mp-id` a released material identifier, rather than asserting that it uniquely identifies a crystal. Source inspection found an identifier collision with incompatible structures. The solver has the unchanged calculation names and structures needed to detect that ambiguity; supplying a correction table in the prompt would pre-solve part of the scientific data validation.

These calculations do not independently establish experimental transfer, spin states, causal effects of geometry or convergence of FEFF parameters. The release does not supply the raw experimental/OCEAN comparison arrays or parameter sweeps needed to turn those topics into self-contained reproduction tasks. None is made a solver requirement here. Intended difficulty is supported by the required scientific work and has not been calibrated on a population of scientific-agent systems.
