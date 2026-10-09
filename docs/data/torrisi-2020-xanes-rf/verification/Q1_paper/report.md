# Q1: published pointwise coordination experiment reproduced

All eight elements, ten prescribed seeds, 38,610 test predictions and 64 published mean/SD comparisons pass. An independent raw-data implementation and a separate solver-bundle execution produce identical test predictions.

| Element | Test accuracy | F1: CN4 | F1: CN5 | F1: CN6 | Test counts: CN4 / CN5 / CN6 |
|---|---:|---:|---:|---:|---|
| Ti | 0.8754 | 0.8153 | 0.8758 | 0.8860 | 38 / 242 / 191 |
| V | 0.8847 | 0.9642 | 0.8207 | 0.8769 | 200 / 224 / 263 |
| Cr | 0.8660 | 0.9428 | 0.6809 | 0.9059 | 48 / 48 / 139 |
| Mn | 0.8012 | 0.6143 | 0.8037 | 0.8130 | 36 / 387 / 358 |
| Fe | 0.8424 | 0.8275 | 0.8321 | 0.8608 | 102 / 309 / 257 |
| Co | 0.8145 | 0.8081 | 0.6870 | 0.8856 | 55 / 108 / 181 |
| Ni | 0.8902 | 0.8310 | 0.7906 | 0.9325 | 15 / 96 / 226 |
| Cu | 0.8506 | 0.6311 | 0.8956 | 0.8190 | 52 / 229 / 57 |

Accuracy and per-class F1 are measured directly against the released coordination labels. All displayed values are means over seeds 42–51. The table and plots reproduce the author-released pointwise results; they replace the previous ExtraTrees/class-weighting illustration.

The reproduced failure pattern includes lower CN4 F1 for Mn/Cu and lower CN5 F1 for Cr/Co. High overall accuracy therefore does not imply equally reliable identification of every coordination class.

Acceptance is fixed: each published mean and population SD must match within 0.00005 in fractional score units plus 1e-12 arithmetic epsilon. This is half a 0.01-percentage-point rounding unit. The separate replay empirically reproduces every published value at that precision; the rule is not a confidence interval or an adjustable performance threshold.

The input cohort, preprocessing, order, oversampling and forest settings follow the pinned source notebooks. The released successive splits yield approximately 81/9/10, while the article describes 80/10/10. The exact released membership is preserved. The pinned modern scikit-learn runtime reproduces the published aggregate results despite the original study using version 0.21.3.

The oversampling-effect ablation is not scored. The paper reports a validation benefit but does not provide a complete paired effect table. These final-model test results do not establish that oversampling helps every element or every class.

The holdout unit is a spectral record. Related structures may cross partitions. Seed-to-seed SD does not measure uncertainty across splits, new materials or experimental spectra. Test labels are excluded from the solver bundle; the benchmark harness must also exclude the full labeled datasets and public evaluator assets.

Sources: Torrisi et al., doi:10.1038/s41524-020-00376-6; author-released pointwise_table_feff.csv; TRIXS commit 6dbcc598c7bea235f464bed91744c1617725b7a8. Data attribution and CC BY 4.0 provenance are retained in the parent provenance.json.
