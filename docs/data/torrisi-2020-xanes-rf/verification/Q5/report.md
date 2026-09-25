# Q5: executed illustrative analysis

Unit-peak normalization increases mean distance MAE for 8/8 elements and decreases mean coordination macro-F1 for 7/8 in this design; many individual coordination intervals remain inconclusive. Dominant permutation-effect bins agree across normalization in 29/64 comparisons, versus 55/64 across fitting seeds and 52/64 across material partitions. Thus useful prediction survives, but neither unchanged accuracy nor unchanged interpretation is supported generally. The normalization effect on attribution exceeds these sampled sources of variability; broader model and population uncertainty remains untested.

This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.

Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.

Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.

Scores below are macro-F1 for coordination and MAE for regression (Å for distance, electron-charge units for Bader labels).

| Element / target | Condition | Mean test score | Range across material holdouts/fits |
|---|---|---:|---:|
| Ti / coord | released | 0.8262 | 0.8028–0.8628 |
| V / coord | released | 0.8725 | 0.8542–0.8811 |
| Cr / coord | released | 0.8605 | 0.8507–0.8744 |
| Mn / coord | released | 0.7476 | 0.7225–0.7733 |
| Fe / coord | released | 0.8056 | 0.7964–0.8160 |
| Co / coord | released | 0.7981 | 0.7885–0.8078 |
| Ni / coord | released | 0.7711 | 0.7446–0.8050 |
| Cu / coord | released | 0.7840 | 0.7619–0.8063 |
| Ti / coord | unit_peak | 0.7869 | 0.7490–0.8035 |
| V / coord | unit_peak | 0.8484 | 0.8432–0.8606 |
| Cr / coord | unit_peak | 0.8333 | 0.8149–0.8461 |
| Mn / coord | unit_peak | 0.7597 | 0.7348–0.8027 |
| Fe / coord | unit_peak | 0.7933 | 0.7857–0.8024 |
| Co / coord | unit_peak | 0.7666 | 0.7594–0.7768 |
| Ni / coord | unit_peak | 0.7493 | 0.7092–0.7868 |
| Cu / coord | unit_peak | 0.7808 | 0.7707–0.7961 |
| Ti / md | released | 0.0162 | 0.0150–0.0172 |
| V / md | released | 0.0139 | 0.0130–0.0148 |
| Cr / md | released | 0.0185 | 0.0177–0.0190 |
| Mn / md | released | 0.0199 | 0.0189–0.0207 |
| Fe / md | released | 0.0180 | 0.0168–0.0193 |
| Co / md | released | 0.0197 | 0.0188–0.0206 |
| Ni / md | released | 0.0161 | 0.0159–0.0165 |
| Cu / md | released | 0.0628 | 0.0611–0.0642 |
| Ti / md | unit_peak | 0.0188 | 0.0174–0.0211 |
| V / md | unit_peak | 0.0167 | 0.0157–0.0175 |
| Cr / md | unit_peak | 0.0214 | 0.0210–0.0217 |
| Mn / md | unit_peak | 0.0232 | 0.0220–0.0244 |
| Fe / md | unit_peak | 0.0217 | 0.0212–0.0222 |
| Co / md | unit_peak | 0.0229 | 0.0216–0.0244 |
| Ni / md | unit_peak | 0.0200 | 0.0192–0.0210 |
| Cu / md | unit_peak | 0.0663 | 0.0652–0.0670 |

Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.

Constant baselines predict the training-majority coordination class or training-median regression label. Mean heldout baseline-to-model gains are:

- coord/released: 0.5768 mean gain, range 0.4762–0.7279 across elements and holdouts. This pooled description does not replace the element-specific scores.
- coord/unit_peak: 0.5584 mean gain, range 0.4537–0.6928 across elements and holdouts. This pooled description does not replace the element-specific scores.
- md/released: 0.0614 mean gain, range 0.0307–0.0928 across elements and holdouts. This pooled description does not replace the element-specific scores.
- md/unit_peak: 0.0582 mean gain, range 0.0268–0.0908 across elements and holdouts. This pooled description does not replace the element-specific scores.

Paired material-holdout comparisons (positive favors the second condition; intervals conditional on fitted models):

| Element / target | Second vs first | Mean gain | Individual 95% intervals |
|---|---|---:|---|
| Ti / coord | unit_peak vs released | -0.0392 | [-0.0379, 0.0301]; [-0.0856, -0.0213]; [-0.1303, -0.0077]; [-0.0740, 0.0118] |
| Ti / md | unit_peak vs released | -0.0026 | [-0.0062, -0.0020]; [-0.0036, -0.0000]; [-0.0041, -0.0007]; [-0.0038, -0.0006] |
| V / coord | unit_peak vs released | -0.0241 | [-0.0594, -0.0170]; [-0.0568, -0.0170]; [-0.0348, 0.0069]; [-0.0291, 0.0161] |
| V / md | unit_peak vs released | -0.0027 | [-0.0038, -0.0016]; [-0.0039, -0.0018]; [-0.0035, -0.0018]; [-0.0039, -0.0020] |
| Cr / coord | unit_peak vs released | -0.0272 | [-0.0823, 0.0037]; [-0.0723, 0.0109]; [-0.0711, -0.0014]; [-0.0437, 0.0368] |
| Cr / md | unit_peak vs released | -0.0029 | [-0.0067, 0.0019]; [-0.0060, 0.0025]; [-0.0076, -0.0009]; [-0.0065, -0.0005] |
| Mn / coord | unit_peak vs released | 0.0122 | [-0.0264, 0.0538]; [-0.0219, 0.0517]; [-0.0041, 0.0789]; [-0.0498, 0.0515] |
| Mn / md | unit_peak vs released | -0.0034 | [-0.0053, -0.0020]; [-0.0051, -0.0021]; [-0.0040, -0.0015]; [-0.0042, -0.0017] |
| Fe / coord | unit_peak vs released | -0.0123 | [-0.0434, 0.0132]; [-0.0453, 0.0171]; [-0.0412, 0.0180]; [-0.0382, 0.0363] |
| Fe / md | unit_peak vs released | -0.0038 | [-0.0067, -0.0036]; [-0.0066, -0.0033]; [-0.0033, -0.0008]; [-0.0044, -0.0017] |
| Co / coord | unit_peak vs released | -0.0315 | [-0.0772, 0.0258]; [-0.0695, 0.0131]; [-0.0713, 0.0011]; [-0.0615, -0.0019] |
| Co / md | unit_peak vs released | -0.0032 | [-0.0055, -0.0022]; [-0.0054, -0.0015]; [-0.0046, -0.0015]; [-0.0048, -0.0008] |
| Ni / coord | unit_peak vs released | -0.0218 | [-0.0739, 0.0443]; [-0.0461, 0.0688]; [-0.0912, 0.0296]; [-0.0854, 0.0195] |
| Ni / md | unit_peak vs released | -0.0038 | [-0.0043, -0.0018]; [-0.0060, -0.0026]; [-0.0044, -0.0018]; [-0.0066, -0.0036] |
| Cu / coord | unit_peak vs released | -0.0032 | [-0.0603, 0.0472]; [-0.0694, 0.0296]; [-0.0546, 0.0656]; [-0.0474, 0.0588] |
| Cu / md | unit_peak vs released | -0.0036 | [-0.0067, 0.0011]; [-0.0052, 0.0027]; [-0.0089, -0.0029]; [-0.0085, -0.0008] |

Intervals crossing zero are inconclusive for direction. Similar scores are not a formal equivalence result: no practical equivalence margin was specified.

Held-out joint permutations test whether prediction relies on energy-localized inputs. Features were grouped by energy midpoint before evaluation; multiscale intervals may extend across neighboring regions. The full interval/degree definitions are in feature_definitions.json. Repeated permutations and holdouts corroborate reliance, but correlated features and out-of-distribution perturbations prevent a causal or unique attribution.

Across paired conditions, the highest-loss energy region agrees in 29/64 comparisons. Agreement in predictive score therefore does not by itself establish agreement in interpretation. localization.json gives region effects and permutation variability; evidence.json separates within-condition and between-condition stability.

- Ti/coord descriptor-midpoint bins: released: 4969.0–4979.4 eV (mean loss increase 0.1975); unit_peak: 4969.0–4979.4 eV (mean loss increase 0.3221). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ti/md descriptor-midpoint bins: released: 5000.2–5010.6 eV (mean loss increase 0.0206); unit_peak: 4969.0–4979.4 eV (mean loss increase 0.0254). The named bin groups feature midpoints; it is not the full physical support of the features.
- V/coord descriptor-midpoint bins: released: 5510.1–5520.6 eV (mean loss increase 0.1877); unit_peak: 5468.0–5478.5 eV (mean loss increase 0.2385). The named bin groups feature midpoints; it is not the full physical support of the features.
- V/md descriptor-midpoint bins: released: 5499.6–5510.1 eV (mean loss increase 0.0555); unit_peak: 5499.6–5510.1 eV (mean loss increase 0.0606). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cr/coord descriptor-midpoint bins: released: 6024.7–6035.2 eV (mean loss increase 0.2468); unit_peak: 6024.7–6035.2 eV (mean loss increase 0.4012). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cr/md descriptor-midpoint bins: released: 6024.7–6035.2 eV (mean loss increase 0.0830); unit_peak: 6024.7–6035.2 eV (mean loss increase 0.0797). The named bin groups feature midpoints; it is not the full physical support of the features.
- Mn/coord descriptor-midpoint bins: released: 6583.9–6594.4 eV (mean loss increase 0.1528); unit_peak: 6541.7–6552.2 eV (mean loss increase 0.2551). The named bin groups feature midpoints; it is not the full physical support of the features.
- Mn/md descriptor-midpoint bins: released: 6583.9–6594.4 eV (mean loss increase 0.0849); unit_peak: 6583.9–6594.4 eV (mean loss increase 0.0405). The named bin groups feature midpoints; it is not the full physical support of the features.
- Fe/coord descriptor-midpoint bins: released: 7136.1–7146.7 eV (mean loss increase 0.1771); unit_peak: 7146.7–7157.2 eV (mean loss increase 0.2996). The named bin groups feature midpoints; it is not the full physical support of the features.
- Fe/md descriptor-midpoint bins: released: 7157.2–7167.8 eV (mean loss increase 0.0613); unit_peak: 7157.2–7167.8 eV (mean loss increase 0.0476). The named bin groups feature midpoints; it is not the full physical support of the features.
- Co/coord descriptor-midpoint bins: released: 7755.4–7765.8 eV (mean loss increase 0.1511); unit_peak: 7744.9–7755.4 eV (mean loss increase 0.3160). The named bin groups feature midpoints; it is not the full physical support of the features.
- Co/md descriptor-midpoint bins: released: 7755.4–7765.8 eV (mean loss increase 0.0629); unit_peak: 7734.4–7744.9 eV (mean loss increase 0.0372). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ni/coord descriptor-midpoint bins: released: 8346.9–8357.4 eV (mean loss increase 0.2370); unit_peak: 8367.8–8378.3 eV (mean loss increase 0.2944). The named bin groups feature midpoints; it is not the full physical support of the features.
- Ni/md descriptor-midpoint bins: released: 8378.3–8388.7 eV (mean loss increase 0.0454); unit_peak: 8336.5–8346.9 eV (mean loss increase 0.0394). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cu/coord descriptor-midpoint bins: released: 9018.8–9029.3 eV (mean loss increase 0.2038); unit_peak: 8987.5–8997.9 eV (mean loss increase 0.1868). The named bin groups feature midpoints; it is not the full physical support of the features.
- Cu/md descriptor-midpoint bins: released: 8987.5–8997.9 eV (mean loss increase 0.0290); unit_peak: 8987.5–8997.9 eV (mean loss increase 0.0404). The named bin groups feature midpoints; it is not the full physical support of the features.
- Across fitting seed changes, mean region-rank correlation is 0.916 and the top region agrees in 55/64 comparisons. This supplies a variability scale for judging normalization changes.
- Across material partition changes, mean region-rank correlation is 0.783 and the top region agrees in 52/64 comparisons. This supplies a variability scale for judging normalization changes.

Normalization is paired within the same material partition and fitting seed; leaf size is selected separately, so the contrast describes the best of this small candidate set under each representation. It does not isolate only a fixed-estimator algebraic effect.

Limitations:
- Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.
- Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.
- Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.
- All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.
- Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.
