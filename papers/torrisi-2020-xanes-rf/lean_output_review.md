# Independent review of lean output compatibility

The revised numerical checker accepts straightforward prediction and partition tables without `design.json`, `metrics.csv`, prescribed condition codes, a `code/` directory, or an exhaustive list of excluded records. This review covers output compatibility; it does not claim a new scientific analysis or model refit.

I independently converted the existing Q1 and Q4 worked outputs into temporary submissions containing exactly five files: `report.md`, `diagnostics.png`, root-level `analysis.py`, `predictions.csv`, and `partitions.csv`. The conversion used the old example's optional manifest only to resolve its opaque run identifiers. The resulting submissions contained no manifest and did not need one during verification.

The prediction columns were `element,property,model,fold,source_row,prediction`. Properties used the raw label names `coordination`, `avg_nn_dists`, and `bader`; model names were ordinary descriptions such as `unweighted_forest` and `multiscale_shape`. Partition columns were `element,property,fold,source_row,membership`, with `training`, `validation`, and `testing` as membership values. Compared models shared partition rows, and excluded source records were omitted.

| Probe | Model/evaluation runs | Prediction rows | Recomputed metrics compared | Maximum difference from existing scores |
|---|---:|---:|---:|---:|
| Q1 | 64 | 37,086 | 320 | 1.11 × 10⁻¹⁶ |
| Q4 | 96 | 47,228 | 288 | 2.22 × 10⁻¹⁶ |

Both checks returned `scientific_review_required` with `scientific_pass: null`. Q1 included 32 spectrum-level runs with shared material IDs across partitions; these were accepted and their overlaps reported. This establishes that a material holdout is not a hidden requirement. These particular runs use identified records, so they do not independently test acceptance of missing material IDs.

The refreshed prompts, evaluator descriptions, and version-3 scientific rubric agree on leaving evaluation design to the solver. Material IDs and source labels have plain field definitions. The rubric judges whether the chosen evaluation supports the claim; it does not require one split strategy. A submission that explicitly claims material separation or a paired comparison must still substantiate that claim. Numerical integrity does not establish scientific validity, rule out fabricated predictions, or prove that submitted code generated them.

The exact conversion program, commands, input and artifact hashes, and result summaries are recorded in `docs/data/torrisi-2020-xanes-rf/verification/lean_output_execution_review.json`. The conversion retained previously executed predictions rather than fitting models. Original runnable analysis source and an existing diagnostic figure were copied solely to exercise the flexible artifact layout. Re-execution of that analysis, its supporting scientific diagnostics, and empirical difficulty calibration are outside this review's scope.
