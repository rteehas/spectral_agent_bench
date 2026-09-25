# Q1: executed illustrative analysis

This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.

Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.

Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.

Scores below are macro-F1 for coordination and MAE for regression (Å for distance, electron-charge units for Bader labels).

| Element / target | Condition | Mean test score | Range across material holdouts/fits |
|---|---|---:|---:|
| Ti / coord | untreated | 0.8343 | 0.8057–0.8628 |
| V / coord | untreated | 0.8773 | 0.8745–0.8801 |
| Cr / coord | untreated | 0.8625 | 0.8507–0.8744 |
| Mn / coord | untreated | 0.7479 | 0.7225–0.7733 |
| Fe / coord | untreated | 0.8088 | 0.8015–0.8160 |
| Co / coord | untreated | 0.7980 | 0.7885–0.8076 |
| Ni / coord | untreated | 0.7748 | 0.7446–0.8050 |
| Cu / coord | untreated | 0.7871 | 0.7680–0.8063 |
| Ti / coord | treated | 0.8302 | 0.8134–0.8470 |
| V / coord | treated | 0.8685 | 0.8662–0.8709 |
| Cr / coord | treated | 0.8660 | 0.8659–0.8661 |
| Mn / coord | treated | 0.7341 | 0.7328–0.7354 |
| Fe / coord | treated | 0.7877 | 0.7794–0.7960 |
| Co / coord | treated | 0.7782 | 0.7701–0.7863 |
| Ni / coord | treated | 0.7853 | 0.7517–0.8189 |
| Cu / coord | treated | 0.7990 | 0.7723–0.8256 |

Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.

Constant baselines predict the training-majority coordination class or training-median regression label. Mean heldout baseline-to-model gains are:

- coord/untreated: 0.5800 mean gain, range 0.4762–0.7269 across elements and holdouts. This pooled description does not replace the element-specific scores.
- coord/treated: 0.5748 mean gain, range 0.4872–0.7177 across elements and holdouts. This pooled description does not replace the element-specific scores.

Paired material-holdout comparisons (positive favors the second condition; intervals conditional on fitted models):

| Element / target | Second vs first | Mean gain | Individual 95% intervals |
|---|---|---:|---|
| Ti / coord | treated vs untreated | -0.0041 | [-0.0284, 0.0460]; [-0.0494, 0.0162] |
| V / coord | treated vs untreated | -0.0088 | [-0.0219, 0.0031]; [-0.0235, 0.0058] |
| Cr / coord | treated vs untreated | 0.0035 | [-0.0315, 0.0146]; [0.0003, 0.0329] |
| Mn / coord | treated vs untreated | -0.0138 | [-0.0633, 0.0911]; [-0.0925, 0.0118] |
| Fe / coord | treated vs untreated | -0.0211 | [-0.0414, -0.0037]; [-0.0380, -0.0007] |
| Co / coord | treated vs untreated | -0.0198 | [-0.0414, 0.0017]; [-0.0415, 0.0015] |
| Ni / coord | treated vs untreated | 0.0105 | [-0.0131, 0.0497]; [-0.0296, 0.0681] |
| Cu / coord | treated vs untreated | 0.0118 | [-0.0788, 0.0055]; [0.0150, 0.1122] |

Intervals crossing zero are inconclusive for direction. Similar scores are not a formal equivalence result: no practical equivalence margin was specified.

Class weighting had positive macro-F1 gain in 6/16 material holdouts; only 2 conditional intervals were wholly above zero. Overall success must therefore be judged by per-class F1 and confusion counts, not accuracy alone.

- Ti: untreated class F1(4,5,6)=0.764, 0.873, 0.866; record versus material macro-F1=0.805 versus 0.834. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- V: untreated class F1(4,5,6)=0.957, 0.825, 0.850; record versus material macro-F1=0.886 versus 0.877. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Cr: untreated class F1(4,5,6)=0.952, 0.728, 0.907; record versus material macro-F1=0.832 versus 0.863. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Mn: untreated class F1(4,5,6)=0.616, 0.847, 0.781; record versus material macro-F1=0.748 versus 0.748. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Fe: untreated class F1(4,5,6)=0.786, 0.832, 0.808; record versus material macro-F1=0.839 versus 0.809. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Co: untreated class F1(4,5,6)=0.816, 0.688, 0.890; record versus material macro-F1=0.809 versus 0.798. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Ni: untreated class F1(4,5,6)=0.695, 0.728, 0.901; record versus material macro-F1=0.759 versus 0.775. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.
- Cu: untreated class F1(4,5,6)=0.647, 0.906, 0.808; record versus material macro-F1=0.797 versus 0.787. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.

Class weighting is one imbalance intervention; failure of this intervention does not show that rare-environment prediction is irreducibly poor. Small class support and unstable material holdouts limit conclusions.

Limitations:
- Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.
- Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.
- Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.
- All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.
- Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.
