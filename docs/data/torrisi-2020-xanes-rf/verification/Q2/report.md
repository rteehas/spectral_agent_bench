# Q2: executed illustrative analysis

This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.

Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.

Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.

Scores below are macro-F1 for coordination and MAE for regression (Å for distance, electron-charge units for Bader labels).

| Element / target | Condition | Mean test score | Range across material holdouts/fits |
|---|---|---:|---:|
| Ti / md | model | 0.0161 | 0.0150–0.0171 |
| V / md | model | 0.0141 | 0.0133–0.0148 |
| Cr / md | model | 0.0184 | 0.0177–0.0190 |
| Mn / md | model | 0.0199 | 0.0192–0.0207 |
| Fe / md | model | 0.0181 | 0.0170–0.0193 |
| Co / md | model | 0.0197 | 0.0188–0.0206 |
| Ni / md | model | 0.0163 | 0.0162–0.0165 |
| Cu / md | model | 0.0624 | 0.0611–0.0638 |

Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.

Constant baselines predict the training-majority coordination class or training-median regression label. Mean heldout baseline-to-model gains are:

- md/model: 0.0614 mean gain, range 0.0308–0.0927 across elements and holdouts. This pooled description does not replace the element-specific scores.

Regimes were defined by the training-distance 10th/90th percentiles. This retrospective error stratification uses test truth to characterize failure; it is not a deployable confidence detector. The training median supplies a non-spectral baseline.

- Ti: short MAE=0.0267 Å, bias=+0.0251 Å; middle MAE=0.0090 Å, bias=+0.0012 Å; long MAE=0.0778 Å, bias=-0.0356 Å.
- V: short MAE=0.0058 Å, bias=+0.0048 Å; middle MAE=0.0128 Å, bias=+0.0026 Å; long MAE=0.0332 Å, bias=-0.0234 Å.
- Cr: short MAE=0.0047 Å, bias=+0.0044 Å; middle MAE=0.0151 Å, bias=+0.0047 Å; long MAE=0.0697 Å, bias=-0.0343 Å.
- Mn: short MAE=0.0285 Å, bias=+0.0266 Å; middle MAE=0.0157 Å, bias=+0.0027 Å; long MAE=0.0430 Å, bias=-0.0370 Å.
- Fe: short MAE=0.0291 Å, bias=+0.0263 Å; middle MAE=0.0135 Å, bias=+0.0029 Å; long MAE=0.0401 Å, bias=-0.0288 Å.
- Co: short MAE=0.0309 Å, bias=+0.0298 Å; middle MAE=0.0148 Å, bias=+0.0018 Å; long MAE=0.0498 Å, bias=-0.0430 Å.
- Ni: short MAE=0.0231 Å, bias=+0.0211 Å; middle MAE=0.0110 Å, bias=+0.0015 Å; long MAE=0.0547 Å, bias=-0.0531 Å.
- Cu: short MAE=0.0965 Å, bias=+0.0965 Å; middle MAE=0.0435 Å, bias=+0.0091 Å; long MAE=0.1705 Å, bias=-0.1610 Å.

Positive tail bias means predicted distances are too long; negative means too short. Tail support, group counts and conditional improvement intervals are in regimes.csv. These estimates describe the supplied computed distribution; experimental reliability is untested.

Limitations:
- Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.
- Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.
- Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.
- All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.
- Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.
