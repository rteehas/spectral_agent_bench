# Full-library simulation-to-measurement transfer

This candidate infers both the phase set and its size. It uses all simulated phases of each chemistry. The true constituent count, measured abundance, experimental candidate identities, and test labels are unavailable to fitting and threshold selection. Phase-average templates use the training repeats. Thresholds and representation fusion are calibrated on 600 generated mixtures from separate validation repeats, with one, two, and three constituents in equal numbers. The calibration abundance is a spectral intensity contribution, not a mass fraction.

Numerical choices for this worked answer: linear interpolation onto 2,001 equally spaced two-theta points from 10.02 to 79.98 degrees; subtraction of each spectrum's tenth-percentile intensity followed by peak-height scaling; and unit L2 normalization of the features used for fitting and prediction. Negative residual intensities are retained. The virtual PDF is sampled on 1,000 equally spaced points from 1 to 40 Å and computed as G(r)=(2/pi) integral Q I(Q) sin(Qr) dQ with nonuniform-Q trapezoidal quadrature, Q=4pi sin(theta)/1.5406 Å, and theta half the recorded angle. This uncorrected transform is not a normalized physical PDF. The angular interval stays within the measured specimens' support and provides one common domain for these illustrative analyses; the simulated-only analyses deliberately discard available higher-angle information. These analyst-selected preprocessing and truncation choices were not swept, so the conclusions do not establish insensitivity to them.

**Li-La-Zr-O, XRD.** Calibrated support threshold 0.150, XRD weight 1.00; calibration exact match 0.538. Test exact match 0.092, micro-F1 0.593, count accuracy 0.383, mean predicted count 1.99, false-positive constituent assignments 97.
The exact-match 95% phase-set cluster-bootstrap interval is [0.008, 0.208], based on 6 distinct phase-set blocks.
Example A_E_017c5016a5c515d3: false inclusions ['La2Zr2O7', 'LiLaO2']; missing phases []. This is an evaluation example, not a case used for tuning.
**Li-La-Zr-O, PDF.** Calibrated support threshold 0.150, XRD weight 0.00; calibration exact match 0.563. Test exact match 0.150, micro-F1 0.703, count accuracy 0.358, mean predicted count 1.56, false-positive constituent assignments 37.
The exact-match 95% phase-set cluster-bootstrap interval is [0.083, 0.217], based on 6 distinct phase-set blocks.
Example A_E_017c5016a5c515d3: false inclusions []; missing phases ['Li2CO3']. This is an evaluation example, not a case used for tuning.
**Li-La-Zr-O, Combined.** Calibrated support threshold 0.150, XRD weight 0.25; calibration exact match 0.575. Test exact match 0.133, micro-F1 0.684, count accuracy 0.392, mean predicted count 1.56, false-positive constituent assignments 41.
The exact-match 95% phase-set cluster-bootstrap interval is [0.058, 0.209], based on 6 distinct phase-set blocks.
Example A_E_017c5016a5c515d3: false inclusions []; missing phases ['Li2CO3']. This is an evaluation example, not a case used for tuning.

**Li-Ti-P-O, XRD.** Calibrated support threshold 0.150, XRD weight 1.00; calibration exact match 0.500. Test exact match 0.000, micro-F1 0.300, count accuracy 0.575, mean predicted count 1.95, false-positive constituent assignments 163.
The exact-match 95% phase-set cluster-bootstrap interval is [0.000, 0.000], based on 6 distinct phase-set blocks.
Example B_E_008a9cff7f7f32ec: false inclusions ['TiP2O9']; missing phases ['Li2TiO3']. This is an evaluation example, not a case used for tuning.
**Li-Ti-P-O, PDF.** Calibrated support threshold 0.100, XRD weight 0.00; calibration exact match 0.560. Test exact match 0.192, micro-F1 0.603, count accuracy 0.467, mean predicted count 2.03, false-positive constituent assignments 98.
The exact-match 95% phase-set cluster-bootstrap interval is [0.142, 0.242], based on 6 distinct phase-set blocks.
Example B_E_008a9cff7f7f32ec: false inclusions ['Li2Ti3O7', 'TiP2O9']; missing phases ['Li2TiO3']. This is an evaluation example, not a case used for tuning.
**Li-Ti-P-O, Combined.** Calibrated support threshold 0.100, XRD weight 0.25; calibration exact match 0.567. Test exact match 0.142, micro-F1 0.606, count accuracy 0.342, mean predicted count 1.91, false-positive constituent assignments 87.
The exact-match 95% phase-set cluster-bootstrap interval is [0.067, 0.217], based on 6 distinct phase-set blocks.
Example B_E_008a9cff7f7f32ec: false inclusions ['Li2Ti3O7', 'TiP2O9']; missing phases ['Li2TiO3']. This is an evaluation example, not a case used for tuning.

Li-La-Zr-O, XRD: 2: 0.000, 4: 0.000, 6: 0.083, 8: 0.000, 10: 0.083, 12: 0.250, 14: 0.250, 16: 0.417, 18: 0.333, 20: 0.500 (minor-phase recall by weight percent).
Li-La-Zr-O, PDF: 2: 0.000, 4: 0.000, 6: 0.083, 8: 0.083, 10: 0.083, 12: 0.333, 14: 0.500, 16: 0.417, 18: 0.500, 20: 0.583 (minor-phase recall by weight percent).
Li-La-Zr-O, Combined: 2: 0.000, 4: 0.000, 6: 0.083, 8: 0.083, 10: 0.083, 12: 0.250, 14: 0.333, 16: 0.417, 18: 0.500, 20: 0.500 (minor-phase recall by weight percent).
Li-Ti-P-O, XRD: 2: 0.000, 4: 0.000, 6: 0.000, 8: 0.000, 10: 0.000, 12: 0.000, 14: 0.000, 16: 0.000, 18: 0.000, 20: 0.000 (minor-phase recall by weight percent).
Li-Ti-P-O, PDF: 2: 0.000, 4: 0.000, 6: 0.000, 8: 0.000, 10: 0.083, 12: 0.250, 14: 0.333, 16: 0.417, 18: 0.417, 20: 0.667 (minor-phase recall by weight percent).
Li-Ti-P-O, Combined: 2: 0.000, 4: 0.000, 6: 0.000, 8: 0.000, 10: 0.083, 12: 0.167, 14: 0.250, 16: 0.417, 18: 0.417, 20: 0.500 (minor-phase recall by weight percent).

Threshold search, template library, and calibration results are saved in design.json; predictions can be rescored directly from source labels. A high constituent-level F1 can coexist with low exact-set recovery and incorrect constituent counts. Threshold transfer is itself part of the experiment: real release mixtures need not follow the synthetic calibration distribution. Test outcomes did not feed back into threshold selection.

Uncertainty resamples unordered phase sets as blocks, preserving repeated compositions and abundance observations. uncertainty.json contains 2,000-resample intervals for overall exact recovery and each count/abundance group. They describe variation in this panel and do not account for training or calibration uncertainty. At a boundary with no observed successes or failures, empirical bootstrap intervals can collapse to a point; this does not imply certainty about performance on future specimens. error_examples.csv records false inclusions and exclusions for three deterministic failures per chemistry/representation, when present.

The experimental panel has only six unordered formula-pair blocks. Treating these as independent resampling units still ignores shared precursor identities across pairs, so the intervals give only a limited description of panel uncertainty.

Li-La-Zr-O: PDF exact recovery exceeds XRD by +0.058; combining scores changes it by -0.017 relative to PDF. Full-library false positives and missed weak components limit transfer; the simulation-selected fusion weight does not establish an experimental improvement.
Li-Ti-P-O: PDF exact recovery exceeds XRD by +0.192; combining scores changes it by -0.050 relative to PDF. Full-library false positives and missed weak components limit transfer; the simulation-selected fusion weight does not establish an experimental improvement.
Polymorph coefficients were summed into formula scores before detection; no four-formula shortlist was used. There are only twelve specimens at each abundance within each chemistry, and ordered major/minor pairs recur across abundance. These measurements are not independent material families. False positives against the full simulation library matter as much as minor-phase recall. The curve is a panel-specific transfer assessment and does not establish a universal mass-fraction detection limit. Measured labels and weight fractions are used exclusively after the predictions for evaluation; simulation coefficients are not estimated mass fractions.
