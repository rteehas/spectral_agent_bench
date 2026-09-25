# Q3: executed illustrative analysis

This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.

Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.

Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.

Scores below are macro-F1 for coordination and MAE for regression (Å for distance, electron-charge units for Bader labels).

| Element / target | Condition | Mean test score | Range across material holdouts/fits |
|---|---|---:|---:|
| Ti / bader | full | 0.0703 | 0.0682–0.0724 |
| V / bader | full | 0.0715 | 0.0709–0.0721 |
| Cr / bader | full | 0.0628 | 0.0619–0.0638 |
| Mn / bader | full | 0.0651 | 0.0635–0.0668 |
| Fe / bader | full | 0.1043 | 0.1026–0.1060 |
| Co / bader | full | 0.0714 | 0.0695–0.0733 |
| Ni / bader | full | 0.0675 | 0.0673–0.0677 |
| Cu / bader | full | 0.0962 | 0.0925–0.0999 |
| Ti / bader | white_line | 0.1000 | 0.0984–0.1016 |
| V / bader | white_line | 0.1431 | 0.1406–0.1456 |
| Cr / bader | white_line | 0.1447 | 0.1415–0.1480 |
| Mn / bader | white_line | 0.1574 | 0.1498–0.1650 |
| Fe / bader | white_line | 0.2101 | 0.1959–0.2242 |
| Co / bader | white_line | 0.1593 | 0.1552–0.1634 |
| Ni / bader | white_line | 0.0923 | 0.0916–0.0930 |
| Cu / bader | white_line | 0.1724 | 0.1712–0.1736 |

Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.

Constant baselines predict the training-majority coordination class or training-median regression label. Mean heldout baseline-to-model gains are:

- bader/full: 0.0791 mean gain, range 0.0246–0.1278 across elements and holdouts. This pooled description does not replace the element-specific scores.
- bader/white_line: 0.0078 mean gain, range -0.0141–0.0415 across elements and holdouts. This pooled description does not replace the element-specific scores.

For this task comparisons.csv stores full first and white_line second, so negative gain favors the full spectrum.

- Ti: full-spectrum MAE reduction relative to white line averages 0.0297 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- V: full-spectrum MAE reduction relative to white line averages 0.0716 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Cr: full-spectrum MAE reduction relative to white line averages 0.0819 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Mn: full-spectrum MAE reduction relative to white line averages 0.0923 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Fe: full-spectrum MAE reduction relative to white line averages 0.1058 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Co: full-spectrum MAE reduction relative to white line averages 0.0879 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Ni: full-spectrum MAE reduction relative to white line averages 0.0248 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.
- Cu: full-spectrum MAE reduction relative to white line averages 0.0762 charge units; 2/2 conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.

Incremental predictive information is model- and cohort-dependent. This analysis does not establish a direct physical inversion or a unique oxidation-state assignment.

Limitations:
- Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.
- Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.
- Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.
- All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.
- Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.
