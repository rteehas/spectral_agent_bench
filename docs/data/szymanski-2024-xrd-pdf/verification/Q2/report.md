# Unknown-cardinality mixture identification

This candidate infers both the phase set and its size. It uses all simulated phases of each chemistry. The true constituent count, measured abundance, experimental candidate identities, and test labels are unavailable to fitting and threshold selection. Phase-average templates use the training repeats. Thresholds and representation fusion are calibrated on 600 generated mixtures from separate validation repeats, with one, two, and three constituents in equal numbers. The calibration abundance is a spectral intensity contribution, not a mass fraction.

Numerical choices for this worked answer: linear interpolation onto 2,001 equally spaced two-theta points from 10.02 to 79.98 degrees; subtraction of each spectrum's tenth-percentile intensity followed by peak-height scaling; and unit L2 normalization of the features used for fitting and prediction. Negative residual intensities are retained. The virtual PDF is sampled on 1,000 equally spaced points from 1 to 40 Å and computed as G(r)=(2/pi) integral Q I(Q) sin(Qr) dQ with nonuniform-Q trapezoidal quadrature, Q=4pi sin(theta)/1.5406 Å, and theta half the recorded angle. This uncorrected transform is not a normalized physical PDF. The angular interval stays within the measured specimens' support and provides one common domain for these illustrative analyses; the simulated-only analyses deliberately discard available higher-angle information. These analyst-selected preprocessing and truncation choices were not swept, so the conclusions do not establish insensitivity to them.

**Li-La-Zr-O, XRD.** Calibrated support threshold 0.150, XRD weight 1.00; calibration exact match 0.490. Test exact match 0.400, micro-F1 0.794, count accuracy 0.532, mean predicted count 2.12, false-positive constituent assignments 227.
The exact-match 95% phase-set cluster-bootstrap interval is [0.365, 0.436], based on 682 distinct phase-set blocks.
Example A_M_00275cb210c13ff4: false inclusions []; missing phases ['ZrO2_137']. This is an evaluation example, not a case used for tuning.
**Li-La-Zr-O, PDF.** Calibrated support threshold 0.150, XRD weight 0.00; calibration exact match 0.513. Test exact match 0.416, micro-F1 0.801, count accuracy 0.499, mean predicted count 2.00, false-positive constituent assignments 157.
The exact-match 95% phase-set cluster-bootstrap interval is [0.381, 0.451], based on 682 distinct phase-set blocks.
Example A_M_00275cb210c13ff4: false inclusions []; missing phases ['ZrO2_137']. This is an evaluation example, not a case used for tuning.
**Li-La-Zr-O, Combined.** Calibrated support threshold 0.150, XRD weight 0.25; calibration exact match 0.520. Test exact match 0.419, micro-F1 0.806, count accuracy 0.510, mean predicted count 2.00, false-positive constituent assignments 150.
The exact-match 95% phase-set cluster-bootstrap interval is [0.382, 0.454], based on 682 distinct phase-set blocks.
Example A_M_00275cb210c13ff4: false inclusions []; missing phases ['ZrO2_137']. This is an evaluation example, not a case used for tuning.

**Li-Ti-P-O, XRD.** Calibrated support threshold 0.150, XRD weight 1.00; calibration exact match 0.503. Test exact match 0.431, micro-F1 0.816, count accuracy 0.512, mean predicted count 2.03, false-positive constituent assignments 146.
The exact-match 95% phase-set cluster-bootstrap interval is [0.400, 0.466], based on 762 distinct phase-set blocks.
Example B_M_000aa4a09933e8cb: false inclusions []; missing phases ['LiPO3_13']. This is an evaluation example, not a case used for tuning.
**Li-Ti-P-O, PDF.** Calibrated support threshold 0.100, XRD weight 0.00; calibration exact match 0.585. Test exact match 0.486, micro-F1 0.839, count accuracy 0.589, mean predicted count 2.23, false-positive constituent assignments 197.
The exact-match 95% phase-set cluster-bootstrap interval is [0.451, 0.521], based on 762 distinct phase-set blocks.
Example B_M_000aa4a09933e8cb: false inclusions []; missing phases ['LiPO3_13']. This is an evaluation example, not a case used for tuning.
**Li-Ti-P-O, Combined.** Calibrated support threshold 0.100, XRD weight 0.00; calibration exact match 0.585. Test exact match 0.486, micro-F1 0.839, count accuracy 0.589, mean predicted count 2.23, false-positive constituent assignments 197.
The exact-match 95% phase-set cluster-bootstrap interval is [0.451, 0.521], based on 762 distinct phase-set blocks.
Example B_M_000aa4a09933e8cb: false inclusions []; missing phases ['LiPO3_13']. This is an evaluation example, not a case used for tuning.

Li-La-Zr-O, XRD: 2: 0.652, 3: 0.147 (exact match by true constituent count).
Li-La-Zr-O, PDF: 2: 0.670, 3: 0.163 (exact match by true constituent count).
Li-La-Zr-O, Combined: 2: 0.675, 3: 0.163 (exact match by true constituent count).
Li-Ti-P-O, XRD: 2: 0.700, 3: 0.163 (exact match by true constituent count).
Li-Ti-P-O, PDF: 2: 0.690, 3: 0.282 (exact match by true constituent count).
Li-Ti-P-O, Combined: 2: 0.690, 3: 0.282 (exact match by true constituent count).

Threshold search, template library, and calibration results are saved in design.json; predictions can be rescored directly from source labels. A high constituent-level F1 can coexist with low exact-set recovery and incorrect constituent counts. Threshold transfer is itself part of the experiment: real release mixtures need not follow the synthetic calibration distribution. Test outcomes did not feed back into threshold selection.

Uncertainty resamples unordered phase sets as blocks, preserving repeated compositions and abundance observations. uncertainty.json contains 2,000-resample intervals for overall exact recovery and each count/abundance group. They describe variation in this panel and do not account for training or calibration uncertainty. At a boundary with no observed successes or failures, empirical bootstrap intervals can collapse to a point; this does not imply certainty about performance on future specimens. error_examples.csv records false inclusions and exclusions for three deterministic failures per chemistry/representation, when present.

Li-La-Zr-O: the highest observed overall exact recovery is 0.419 (Combined); even this method misses the full set in 58.1% of mixtures. The larger third-phase loss and count errors show that identity ranking alone does not solve decomposition.
Li-Ti-P-O: the highest observed overall exact recovery is 0.486 (PDF); even this method misses the full set in 51.4% of mixtures. The larger third-phase loss and count errors show that identity ranking alone does not solve decomposition.
Changing the true number of phases also changes composition and relative intensities in these released mixtures. A two-versus-three-phase contrast is consequently descriptive, not a causal isolation of peak overlap. The model can return one or more constituents; it never truncates a ranking to the true count. Generated calibration mixtures use only single-phase spectra, and every released pooled mixture is held out.
