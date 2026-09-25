# Independent research-question quality review

**Verdict: pass after two minor contract clarifications.** All four questions require substantial computation and an evidence-backed scientific interpretation. Their solver prompts are standalone, do not refer to a paper or figure, and do not reveal which representation should perform better. The questions concern powder XRD and virtual PDFs, not XANES.

## Question-level assessment

| Question | Verdict | Distinct research step and required work |
|---|---|---|
| Q1 | Pass | Establish whether a change of representation or score averaging improves single-phase identification. Requires preprocessing, numerical transformation, fresh supervised fits on prescribed training records, held-out predictions, and paired error analysis. |
| Q2 | Pass | Determine how well constituent identities can be recovered in mixtures with increasing phase count. Requires constructing references from training spectra, constrained fitting in two representations, combining scores, and evaluating exact phase sets and partial recovery. |
| Q3 | Pass | Assess how added noise and smooth background interact with distance-window selection. Requires repeated paired perturbations of all relevant released baselines, numerical transforms, per-window distortion and signal-retention measurements, and a quantified window recommendation. |
| Q4 | Pass | Test whether simulation-derived references identify secondary phases in measured mixtures across abundance. Requires transfer to experimental scan grids, handling polymorph-to-formula scoring, blind spectral fitting, and abundance-stratified evaluation. |

Q2 and Q4 share a fitting method but test different scientific limitations: recovery in simulated mixtures versus transfer to measured mixtures and minority-phase sensitivity. Q1 trains a supervised model instead of using template decomposition. Q3 is a perturbation and representation-design experiment rather than another classification score calculation. None can be answered by reading a provided result table or inspecting a filename.

## Background, input boundary, and hand-holding

Each short background supplies only the material, representation, label, or experimental-design information needed to interpret its inputs. No prompt mentions the publication, requests figure reproduction, assumes PDF superiority, or gives an expected number. Source attribution in the input README identifies the public data; it is not a worked answer.

The numerical protocol is detailed, but its details fix consequential choices needed to compare independently executed answers: angular support, preprocessing, sine-transform convention, training partition, models, fusion, perturbation seeds, window boundaries, and metrics. It provides no fitted weights, derived features, predictions, or scientific findings. The output schema defines the answer format. Solvers must still implement an analysis and interpret its results. Removing these numerical choices while retaining exact reference checks would make the task under-specified. Question-specific protocol extracts could reduce reading burden, but are optional.

Every question includes its complete raw numeric inputs and metadata. References to Q1 or Q2 inside the protocol reuse definitions, not another question's outputs. The records are the earliest released numeric spectra, with simulation artifacts already present; they are not detector frames or pristine ideal patterns. The Q3 perturbations are generated during solving. No pretrained model is a solver input.

Labels copied from the original filenames are supplied separately because these are scientific evaluation tasks. The contract explicitly prohibits using target labels during inference. Anonymous array keys remove labels from the spectrum names, but separate labels remain readable: an output-only checker cannot prove label separation. An actual benchmark run must preserve this stated scientific boundary and retain execution traces. This limitation is acknowledged, rather than claimed to be solved by renaming files.

## Clarifications corrected and rechecked

- **QUALITY-01 — split trace semantics:** the initial output schema described the trace as training/test IDs “used,” although Q2 and Q4 record unused single-phase test partitions. The final schema explicitly identifies the complete reference partition and locates evaluated mixture IDs in `predictions.csv`. Resolved.
- **QUALITY-02 — protocol dependencies:** the initial README stated that only a question's own protocol section and common settings apply. Q2 and Q4 explicitly reuse definitions from other sections. The final README includes explicitly referenced sections and confirms that no prior answer is required. Resolved.

## Scientific scope and verification boundary

These are controlled ridge and template baseline experiments derived from research stages, not historical CNN reproductions. Q1 withholds augmented repeats of represented phase identities; it does not establish recognition of unseen phases. Q2 receives the true phase count, and its two- and three-phase groups also differ in composition, so their score difference does not isolate a causal effect of phase count. Q3 measures distortion and sampled energy, not retained classification accuracy. Q4 uses a known four-formula candidate library per chemistry, merges polymorphs for scoring, and cannot turn intensity coefficients into mass fractions or establish a universal detection limit. The prompts and protocol support appropriately limited conclusions.

This review assesses question quality, input sufficiency, and consistency of the solver contract. It does not substitute for the separate execution rerun or independent verification audit. Numerical references and scientific interpretations must be assessed under those reviews. The machine-readable report records the reviewed solver-prompt projection and contract hashes; evaluator-only results can be regenerated without changing the reviewed question text.
