# Representation reliability and learner dependence

This is one executed answer with analyst-chosen methods, not a benchmark-prescribed fitting recipe.

Two distinct classifier families were trained and tuned separately on XRD and uncorrected sine-transform virtual PDFs. Hyperparameters and the XRD/PDF averaging weight were selected using validation spectra. Only then were the held-out test spectra scored. Both representations share the same test examples. The bootstrap resamples phase identities, carrying the repeated spectra for each phase together.

Numerical choices for this worked answer: linear interpolation onto 2,001 equally spaced two-theta points from 10.02 to 79.98 degrees; subtraction of each spectrum's tenth-percentile intensity followed by peak-height scaling; and unit L2 normalization of the features used for fitting and prediction. Negative residual intensities are retained. The virtual PDF is sampled on 1,000 equally spaced points from 1 to 40 Å and computed as G(r)=(2/pi) integral Q I(Q) sin(Qr) dQ with nonuniform-Q trapezoidal quadrature, Q=4pi sin(theta)/1.5406 Å, and theta half the recorded angle. This uncorrected transform is not a normalized physical PDF. The angular interval stays within the measured specimens' support and provides one common domain for these illustrative analyses; the simulated-only analyses deliberately discard available higher-angle information. These analyst-selected preprocessing and truncation choices were not swept, so the conclusions do not establish insensitivity to them.

**Li-La-Zr-O, Ridge.** Test accuracy: XRD 0.955, PDF 0.973, Combined 0.973. Validation chose an XRD weight of 0.00.
Paired outcomes: {'both_correct': 107, 'xrd_only_correct': 0, 'pdf_only_correct': 2, 'neither_correct': 3}.
PDF_minus_XRD: +0.018, phase-block bootstrap 95% interval [+0.000, +0.045].
Combined_minus_XRD: +0.018, phase-block bootstrap 95% interval [+0.000, +0.045].
Combined_minus_PDF: +0.000, phase-block bootstrap 95% interval [+0.000, +0.000].

**Li-La-Zr-O, RBF-SVM.** Test accuracy: XRD 0.982, PDF 0.964, Combined 0.991. Validation chose an XRD weight of 0.50.
Paired outcomes: {'both_correct': 107, 'xrd_only_correct': 3, 'pdf_only_correct': 1, 'neither_correct': 1}.
PDF_minus_XRD: -0.018, phase-block bootstrap 95% interval [-0.054, +0.018].
Combined_minus_XRD: +0.009, phase-block bootstrap 95% interval [+0.000, +0.027].
Combined_minus_PDF: +0.027, phase-block bootstrap 95% interval [+0.000, +0.054].

**Li-Ti-P-O, Ridge.** Test accuracy: XRD 0.945, PDF 0.959, Combined 0.959. Validation chose an XRD weight of 0.00.
Paired outcomes: {'both_correct': 136, 'xrd_only_correct': 1, 'pdf_only_correct': 3, 'neither_correct': 5}.
PDF_minus_XRD: +0.014, phase-block bootstrap 95% interval [-0.013, +0.042].
Combined_minus_XRD: +0.014, phase-block bootstrap 95% interval [-0.013, +0.042].
Combined_minus_PDF: +0.000, phase-block bootstrap 95% interval [+0.000, +0.000].

**Li-Ti-P-O, RBF-SVM.** Test accuracy: XRD 0.931, PDF 0.972, Combined 0.972. Validation chose an XRD weight of 0.00.
Paired outcomes: {'both_correct': 133, 'xrd_only_correct': 2, 'pdf_only_correct': 8, 'neither_correct': 2}.
PDF_minus_XRD: +0.041, phase-block bootstrap 95% interval [+0.014, +0.075].
Combined_minus_XRD: +0.041, phase-block bootstrap 95% interval [+0.014, +0.075].
Combined_minus_PDF: +0.000, phase-block bootstrap 95% interval [+0.000, +0.000].

For Li-La-Zr-O, the representation ranking changes with the learner. The tested learner choices therefore do not support a learner-independent representation advantage.
Fusion exceeds both standalone representations in 1 of 2 tested learner families; it is not a consistent gain across learners.
For Li-Ti-P-O, PDF ranks above XRD under both learners. The tested learner choices therefore agree on the direction, although the uncertainty differs.
Fusion exceeds both standalone representations in 0 of 2 tested learner families; it is not a consistent gain across learners.

A representation-only claim requires the direction and size of its advantage to survive the learner comparison. A few discordant errors alone do not establish a reproducible fusion benefit; compare the paired intervals and both constituent baselines. The code reports all three contrasts, including when validation-selected fusion collapses to one representation.

The test set holds out augmentations of known structures, not unseen chemical phases. The released spectra already contain simulation artifacts; their repeats may share generating assumptions. The uncorrected transform discards phase-space information through truncation and resampling and is not a normalized physical PDF. Small sample counts, training-set reuse, softmax score scale differences, and a single split constrain these conclusions. The phase-block interval addresses repeated-phase dependence in the test panel, not uncertainty over training a new model.

All tuning values and split IDs are saved in design.json and splits.csv. comparison.json contains the paired uncertainty and discordant-error counts.
