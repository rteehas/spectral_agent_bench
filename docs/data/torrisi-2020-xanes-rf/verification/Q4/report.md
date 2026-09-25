# Q4: executed illustrative analysis

This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.

Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.

Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.

Scores below are macro-F1 for coordination and MAE for regression (Å for distance, electron-charge units for Bader labels).

| Element / target | Condition | Mean test score | Range across material holdouts/fits |
|---|---|---:|---:|
| Ti / coord | pointwise | 0.8343 | 0.8057–0.8628 |
| V / coord | pointwise | 0.8773 | 0.8745–0.8801 |
| Cr / coord | pointwise | 0.8625 | 0.8507–0.8744 |
| Mn / coord | pointwise | 0.7479 | 0.7225–0.7733 |
| Fe / coord | pointwise | 0.8088 | 0.8015–0.8160 |
| Co / coord | pointwise | 0.7980 | 0.7885–0.8076 |
| Ni / coord | pointwise | 0.7748 | 0.7446–0.8050 |
| Cu / coord | pointwise | 0.7871 | 0.7680–0.8063 |
| Ti / coord | multiscale | 0.8206 | 0.7848–0.8563 |
| V / coord | multiscale | 0.8720 | 0.8616–0.8824 |
| Cr / coord | multiscale | 0.8473 | 0.8422–0.8523 |
| Mn / coord | multiscale | 0.7538 | 0.7244–0.7833 |
| Fe / coord | multiscale | 0.8041 | 0.8003–0.8079 |
| Co / coord | multiscale | 0.7890 | 0.7767–0.8013 |
| Ni / coord | multiscale | 0.7914 | 0.7684–0.8144 |
| Cu / coord | multiscale | 0.8004 | 0.7832–0.8176 |
| Ti / md | pointwise | 0.0161 | 0.0150–0.0171 |
| V / md | pointwise | 0.0141 | 0.0133–0.0148 |
| Cr / md | pointwise | 0.0184 | 0.0177–0.0190 |
| Mn / md | pointwise | 0.0199 | 0.0192–0.0207 |
| Fe / md | pointwise | 0.0181 | 0.0170–0.0193 |
| Co / md | pointwise | 0.0197 | 0.0188–0.0206 |
| Ni / md | pointwise | 0.0163 | 0.0162–0.0165 |
| Cu / md | pointwise | 0.0624 | 0.0611–0.0638 |
| Ti / md | multiscale | 0.0169 | 0.0150–0.0188 |
| V / md | multiscale | 0.0144 | 0.0135–0.0152 |
| Cr / md | multiscale | 0.0178 | 0.0178–0.0179 |
| Mn / md | multiscale | 0.0197 | 0.0187–0.0207 |
| Fe / md | multiscale | 0.0187 | 0.0182–0.0192 |
| Co / md | multiscale | 0.0197 | 0.0188–0.0205 |
| Ni / md | multiscale | 0.0169 | 0.0166–0.0171 |
| Cu / md | multiscale | 0.0634 | 0.0633–0.0636 |
| Ti / bader | pointwise | 0.0703 | 0.0682–0.0724 |
| V / bader | pointwise | 0.0715 | 0.0709–0.0721 |
| Cr / bader | pointwise | 0.0628 | 0.0619–0.0638 |
| Mn / bader | pointwise | 0.0651 | 0.0635–0.0668 |
| Fe / bader | pointwise | 0.1043 | 0.1026–0.1060 |
| Co / bader | pointwise | 0.0714 | 0.0695–0.0733 |
| Ni / bader | pointwise | 0.0675 | 0.0673–0.0677 |
| Cu / bader | pointwise | 0.0962 | 0.0925–0.0999 |
| Ti / bader | multiscale | 0.0688 | 0.0681–0.0695 |
| V / bader | multiscale | 0.0724 | 0.0719–0.0729 |
| Cr / bader | multiscale | 0.0642 | 0.0618–0.0667 |
| Mn / bader | multiscale | 0.0671 | 0.0670–0.0673 |
| Fe / bader | multiscale | 0.1035 | 0.1019–0.1050 |
| Co / bader | multiscale | 0.0726 | 0.0713–0.0740 |
| Ni / bader | multiscale | 0.0687 | 0.0676–0.0698 |
| Cu / bader | multiscale | 0.0984 | 0.0970–0.0997 |

Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.

Constant baselines predict the training-majority coordination class or training-median regression label. Mean heldout baseline-to-model gains are:

- coord/pointwise: 0.5800 mean gain, range 0.4762–0.7269 across elements and holdouts. This pooled description does not replace the element-specific scores.
- coord/multiscale: 0.5785 mean gain, range 0.4781–0.7292 across elements and holdouts. This pooled description does not replace the element-specific scores.
- md/pointwise: 0.0614 mean gain, range 0.0308–0.0927 across elements and holdouts. This pooled description does not replace the element-specific scores.
- md/multiscale: 0.0611 mean gain, range 0.0291–0.0939 across elements and holdouts. This pooled description does not replace the element-specific scores.
- bader/pointwise: 0.0791 mean gain, range 0.0246–0.1278 across elements and holdouts. This pooled description does not replace the element-specific scores.
- bader/multiscale: 0.0783 mean gain, range 0.0224–0.1241 across elements and holdouts. This pooled description does not replace the element-specific scores.

Paired material-holdout comparisons (positive favors the second condition; intervals conditional on fitted models):

| Element / target | Second vs first | Mean gain | Individual 95% intervals |
|---|---|---:|---|
| Ti / coord | multiscale vs pointwise | -0.0137 | [-0.0477, 0.0028]; [-0.0437, 0.0273] |
| Ti / md | multiscale vs pointwise | -0.0009 | [-0.0030, -0.0004]; [-0.0010, 0.0013] |
| Ti / bader | multiscale vs pointwise | 0.0015 | [-0.0068, 0.0064]; [-0.0012, 0.0063] |
| V / coord | multiscale vs pointwise | -0.0053 | [-0.0119, 0.0154]; [-0.0299, 0.0015] |
| V / md | multiscale vs pointwise | -0.0003 | [-0.0009, 0.0005]; [-0.0011, 0.0001] |
| V / bader | multiscale vs pointwise | -0.0009 | [-0.0030, 0.0018]; [-0.0038, 0.0017] |
| Cr / coord | multiscale vs pointwise | -0.0153 | [-0.0490, 0.0050]; [-0.0316, 0.0124] |
| Cr / md | multiscale vs pointwise | 0.0005 | [-0.0006, 0.0027]; [-0.0020, 0.0019] |
| Cr / bader | multiscale vs pointwise | -0.0014 | [-0.0041, 0.0048]; [-0.0091, 0.0027] |
| Mn / coord | multiscale vs pointwise | 0.0059 | [-0.0378, 0.0422]; [-0.0093, 0.0378] |
| Mn / md | multiscale vs pointwise | 0.0002 | [-0.0009, 0.0007]; [-0.0005, 0.0012] |
| Mn / bader | multiscale vs pointwise | -0.0020 | [-0.0035, 0.0028]; [-0.0069, -0.0001] |
| Fe / coord | multiscale vs pointwise | -0.0047 | [-0.0096, 0.0262]; [-0.0358, 0.0038] |
| Fe / md | multiscale vs pointwise | -0.0006 | [-0.0020, -0.0005]; [-0.0014, 0.0016] |
| Fe / bader | multiscale vs pointwise | 0.0008 | [-0.0041, 0.0040]; [-0.0036, 0.0057] |
| Co / coord | multiscale vs pointwise | -0.0090 | [-0.0145, 0.0442]; [-0.0602, 0.0008] |
| Co / md | multiscale vs pointwise | 0.0000 | [-0.0009, 0.0009]; [-0.0011, 0.0010] |
| Co / bader | multiscale vs pointwise | -0.0013 | [-0.0049, 0.0032]; [-0.0068, 0.0026] |
| Ni / coord | multiscale vs pointwise | 0.0166 | [-0.0302, 0.0465]; [-0.0070, 0.0691] |
| Ni / md | multiscale vs pointwise | -0.0005 | [-0.0012, 0.0009]; [-0.0020, -0.0002] |
| Ni / bader | multiscale vs pointwise | -0.0013 | [-0.0037, 0.0028]; [-0.0066, 0.0019] |
| Cu / coord | multiscale vs pointwise | 0.0133 | [-0.0229, 0.0533]; [-0.0207, 0.0451] |
| Cu / md | multiscale vs pointwise | -0.0010 | [-0.0016, 0.0024]; [-0.0054, 0.0002] |
| Cu / bader | multiscale vs pointwise | -0.0022 | [-0.0050, 0.0052]; [-0.0112, 0.0026] |

Intervals crossing zero are inconclusive for direction. Similar scores are not a formal equivalence result: no practical equivalence margin was specified.

Held-out joint permutations test whether prediction relies on energy-localized inputs. Features were grouped by energy midpoint before evaluation; multiscale intervals may extend across neighboring regions. The full interval/degree definitions are in feature_definitions.json. Repeated permutations and holdouts corroborate reliance, but correlated features and out-of-distribution perturbations prevent a causal or unique attribution.

Across paired conditions, the highest-loss energy region agrees in 29/48 comparisons. Agreement in predictive score therefore does not by itself establish agreement in interpretation. localization.json gives region effects and permutation variability; evidence.json separates within-condition and between-condition stability.

- Ti/coord descriptor-midpoint bins: pointwise: 4969.0–4979.4 eV (mean loss increase 0.1866); multiscale: 4969.0–4979.4 eV (mean loss increase 0.1772). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ti/md descriptor-midpoint bins: pointwise: 5000.2–5010.6 eV (mean loss increase 0.0215); multiscale: 5000.2–5010.6 eV (mean loss increase 0.0207). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ti/bader descriptor-midpoint bins: pointwise: 4989.8–5000.2 eV (mean loss increase 0.0401); multiscale: 4989.8–5000.2 eV (mean loss increase 0.0294). The named bin groups feature midpoints; it is not the full physical support of the features.
- V/coord descriptor-midpoint bins: pointwise: 5510.1–5520.6 eV (mean loss increase 0.1956); multiscale: 5468.0–5478.5 eV (mean loss increase 0.1650). The named bin groups feature midpoints; it is not the full physical support of the features.
- V/md descriptor-midpoint bins: pointwise: 5499.6–5510.1 eV (mean loss increase 0.0547); multiscale: 5499.6–5510.1 eV (mean loss increase 0.0451). The named bin groups feature midpoints; it is not the full physical support of the features.
- V/bader descriptor-midpoint bins: pointwise: 5499.6–5510.1 eV (mean loss increase 0.0993); multiscale: 5499.6–5510.1 eV (mean loss increase 0.0838). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cr/coord descriptor-midpoint bins: pointwise: 6024.7–6035.2 eV (mean loss increase 0.2623); multiscale: 6035.2–6045.7 eV (mean loss increase 0.0834). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cr/md descriptor-midpoint bins: pointwise: 6024.7–6035.2 eV (mean loss increase 0.0796); multiscale: 6024.7–6035.2 eV (mean loss increase 0.0583). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cr/bader descriptor-midpoint bins: pointwise: 6035.2–6045.7 eV (mean loss increase 0.0740); multiscale: 6024.7–6035.2 eV (mean loss increase 0.0403). The named bin groups feature midpoints; it is not the full physical support of the features.
- Mn/coord descriptor-midpoint bins: pointwise: 6583.9–6594.4 eV (mean loss increase 0.1649); multiscale: 6552.2–6562.8 eV (mean loss increase 0.0907). The named bin groups feature midpoints; it is not the full physical support of the features.
- Mn/md descriptor-midpoint bins: pointwise: 6583.9–6594.4 eV (mean loss increase 0.0885); multiscale: 6583.9–6594.4 eV (mean loss increase 0.0457). The named bin groups feature midpoints; it is not the full physical support of the features.
- Mn/bader descriptor-midpoint bins: pointwise: 6583.9–6594.4 eV (mean loss increase 0.0990); multiscale: 6583.9–6594.4 eV (mean loss increase 0.0687). The named bin groups feature midpoints; it is not the full physical support of the features.
- Fe/coord descriptor-midpoint bins: pointwise: 7136.1–7146.7 eV (mean loss increase 0.1761); multiscale: 7146.7–7157.2 eV (mean loss increase 0.1385). The named bin groups feature midpoints; it is not the full physical support of the features.
- Fe/md descriptor-midpoint bins: pointwise: 7157.2–7167.8 eV (mean loss increase 0.0626); multiscale: 7146.7–7157.2 eV (mean loss increase 0.0365). The named bin groups feature midpoints; it is not the full physical support of the features.
- Fe/bader descriptor-midpoint bins: pointwise: 7157.2–7167.8 eV (mean loss increase 0.0590); multiscale: 7157.2–7167.8 eV (mean loss increase 0.0559). The named bin groups feature midpoints; it is not the full physical support of the features.
- Co/coord descriptor-midpoint bins: pointwise: 7755.4–7765.8 eV (mean loss increase 0.1546); multiscale: 7724.0–7734.4 eV (mean loss increase 0.2447). The named bin groups feature midpoints; it is not the full physical support of the features.
- Co/md descriptor-midpoint bins: pointwise: 7755.4–7765.8 eV (mean loss increase 0.0646); multiscale: 7744.9–7755.4 eV (mean loss increase 0.0394). The named bin groups feature midpoints; it is not the full physical support of the features.
- Co/bader descriptor-midpoint bins: pointwise: 7755.4–7765.8 eV (mean loss increase 0.0915); multiscale: 7755.4–7765.8 eV (mean loss increase 0.0881). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ni/coord descriptor-midpoint bins: pointwise: 8346.9–8357.4 eV (mean loss increase 0.2282); multiscale: 8346.9–8357.4 eV (mean loss increase 0.3062). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ni/md descriptor-midpoint bins: pointwise: 8378.3–8388.7 eV (mean loss increase 0.0453); multiscale: 8378.3–8388.7 eV (mean loss increase 0.0225). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ni/bader descriptor-midpoint bins: pointwise: 8336.5–8346.9 eV (mean loss increase 0.0263); multiscale: 8336.5–8346.9 eV (mean loss increase 0.0205). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cu/coord descriptor-midpoint bins: pointwise: 9018.8–9029.3 eV (mean loss increase 0.2330); multiscale: 8997.9–9008.4 eV (mean loss increase 0.1934). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cu/md descriptor-midpoint bins: pointwise: 8987.5–8997.9 eV (mean loss increase 0.0297); multiscale: 8987.5–8997.9 eV (mean loss increase 0.0272). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cu/bader descriptor-midpoint bins: pointwise: 9018.8–9029.3 eV (mean loss increase 0.0599); multiscale: 9018.8–9029.3 eV (mean loss increase 0.0599). The named bin groups feature midpoints; it is not the full physical support of the features.

The 51 quadratic descriptors retain coarse amplitude/slope/curvature across three scales, while discarding residual within-window structure. shape_families.csv tests each degree family jointly on held-out data. Each family can be redundant across scales, so its loss increase is conditional on the remaining representation. Ranking families without this perturbation evidence would overstate interpretation.
- coord mean loss increases by coefficient degree0/1/2: 0.3786, 0.0709, 0.0561. Aggregation is descriptive; individual elements and runs can differ.
- md mean loss increases by coefficient degree0/1/2: 0.0528, 0.0343, 0.0083. Aggregation is descriptive; individual elements and runs can differ.
- bader mean loss increases by coefficient degree0/1/2: 0.0871, 0.0378, 0.0151. Aggregation is descriptive; individual elements and runs can differ.

Limitations:
- Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.
- Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.
- Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.
- All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.
- Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.
