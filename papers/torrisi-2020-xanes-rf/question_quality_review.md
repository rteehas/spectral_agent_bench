# Independent question-quality review: open scientific tasks

This review supersedes the earlier review that endorsed the supplied protocol. That endorsement was too permissive: prescribing the spectrum screens, exact data partitions, estimators, feature construction, repeated seeds and attribution calculation substantially reduced the scientific reasoning being assessed. Removing expected numerical values was not sufficient to make those prompts a difficult research benchmark.

## Review standard

The solver should receive eight released spectral-data projections and a standalone scientific question. Necessary context consists of measurement type, field definitions, units, unavailable values and provenance limitations. Output requirements should specify only the evidence needed to audit an answer. Numerical algorithms, data curation, partitioning, model selection, uncertainty estimation, feature construction and interpretation must remain decisions for the solver to justify.

A prompt can define its scientific intervention without becoming a recipe. Coordination classes 4/5/6 define the population of interest; white-line position defines the single-descriptor comparison; division by maximum absorption defines the normalization intervention. These definitions do not prescribe an estimator or an expected result.

## Distinct sources of difficulty

- **Q1 — coordination imbalance:** distinguish useful prediction of uncommon environments from aggregate accuracy; establish whether an imbalance treatment is beneficial through a defensible comparison. A majority-class model or an accuracy table alone cannot settle this question.
- **Q2 — distance reliability:** identify where distance inference fails, distinguish systematic bias from scatter, and quantify the evidential limits of sparsely sampled extremes. A global regression score alone is insufficient.
- **Q3 — charge information:** test the incremental predictive information of the spectrum over a physically interpretable white-line descriptor. Peak definition, model capacity, fair comparison and uncertainty matter; full spectra are not assumed to win.
- **Q4 — spectral representation:** design and assess a multiscale shape representation, while connecting predictive evidence to target-specific energy or shape associations. Descriptor construction and trustworthy interpretation remain research work.
- **Q5 — normalization:** separate predictive and interpretive consequences of removing the intensity scale from ordinary fitting and sampling variation. Similar scores cannot establish identical spectral interpretation, and changed rankings alone cannot establish a physical mechanism.

Each question requires substantial interaction with spectra and labels, experimental design, numerical modeling and evidence assessment. Each is independently answerable from its own complete input bundle. None requires an answer to another question or reconstruction of upstream data that the release does not contain.

## Fair verification

A valid answer may use different defensible data screens, partitions, estimators, descriptors or uncertainty methods, and may support a null or negative finding. It must not be rejected merely for disagreeing with the candidate workflow's scores, seeds, feature count, rankings or qualitative conclusions. Exact truth is available for input identity, released labels and arithmetic recomputed from submitted predictions. Whether an experimental comparison supports its scientific claim requires an explicit research-quality review.

Numerical screening is necessary but insufficient. A fabricated scientific narrative or an uninformative constant model can be internally consistent. Review must assess meaningful baselines, sample coverage, fair comparisons, uncertainty, interpretation and the match between the evaluation population and the claimed population. Tail and minority-class conclusions must acknowledge sparse or absent groups. Attributions must be compared on a scientifically comparable domain and cannot be treated as unique causal explanations.

Known material identifiers cover only the `scrape` provenance in these inputs. The `feff` provenance lacks material IDs. Grouped evaluation can assess generalization to held-out known identifiers, but it cannot establish that unidentified records are distinct materials or that this subset represents the whole release. Solver methods must account for this limitation; unknown IDs must not be silently treated as evidence of unique materials. Repeated estimator seeds alone measure fitting randomness, not uncertainty over sampled materials.

## Input isolation and scope

The public review site intentionally exposes source identity, worked workflows and reference outputs. Calling these references “held back” describes their evaluator role, not a security boundary. A blind benchmark must use the exported solver-only bundle and prevent access to the review repository, reference artifacts and site. The export must contain the prompt and the eight gzip JSONL files only. Its prompt should use generic local input paths rather than URLs containing the paper identifier.

The spectra are already processed 100-point release arrays. They are the earliest publicly supplied spectral records, not detector-raw data or native FEFF outputs. The task does not justify claims of transfer to experimental spectra, structural families, unknown database aliases or unrecorded materials.

## Final-review status

The machine-readable companion records the exact reviewed revisions, prompt checks and final verdict. This document reviews question quality and contract fairness. Separate agents assess candidate execution and the correctness of the verification loop; successful question framing must not be conflated with complete scientific validation of a worked example.
