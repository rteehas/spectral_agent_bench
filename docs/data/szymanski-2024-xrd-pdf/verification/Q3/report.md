# Does artifact suppression preserve useful phase information?

All 53 Li-Ti-P-O simulated phases were included. The training, validation, and test repeats are disjoint within each phase. A ridge classifier was trained on clean released spectra in each representation, and its regularization was selected using clean validation spectra. Clean here means no newly added artifact: the released simulation already contains perturbations. Gaussian noise and broad smooth backgrounds were then added to validation and held-out test spectra separately. Candidate distance windows were compared using both phase-identification accuracy and distortion; retained signal energy is not a substitute for classification performance.

**Selected window: r5_40.** The selection maximized validation accuracy after equal weighting of clean, noise, and background artifact families. It did not use held-out classification labels. The complete window search is retained, so selection costs and failures are visible.

**XRD.** Artifact-balanced validation accuracy 0.937; held-out accuracy clean/noise/background 0.945/0.946/0.900.
**r1_5.** Artifact-balanced validation accuracy 0.490; held-out accuracy clean/noise/background 0.641/0.625/0.097.
**r5_40.** Artifact-balanced validation accuracy 0.974; held-out accuracy clean/noise/background 0.945/0.945/0.941.
**r1_40.** Artifact-balanced validation accuracy 0.894; held-out accuracy clean/noise/background 0.959/0.957/0.707.
**r40_120.** Artifact-balanced validation accuracy 0.874; held-out accuracy clean/noise/background 0.848/0.844/0.848.
Selected-window minus XRD accuracy for clean: +0.000, phase-block bootstrap 95% interval [-0.027, +0.027]. Noise draws/severities are averaged within spectrum before resampling phase identities.
Selected-window minus XRD accuracy for noise: -0.001, phase-block bootstrap 95% interval [-0.026, +0.024]. Noise draws/severities are averaged within spectrum before resampling phase identities.
Selected-window minus XRD accuracy for background: +0.041, phase-block bootstrap 95% interval [+0.007, +0.081]. Noise draws/severities are averaged within spectrum before resampling phase identities.

The validation-selected r5_40 window changes clean held-out accuracy by -0.014 relative to the full 1–40 Å window. Its background comparison shows whether the loss of low-r information buys actual identification robustness rather than merely smaller numerical distortion. The phase-block confidence intervals above quantify that tradeoff on the held-out panel.

A window is useful only when its apparent artifact resistance coincides with retained discriminatory information. The high-r window can contain little original signal and a large relative distortion, while a short low-r window can exclude distinguishing oscillations. The held-out curves determine which tradeoff actually works in this experiment; no universal optimal range is claimed.

The 12-pattern evidence.npz audit subset stores the exact preprocessed clean XRD, perturbed XRD, clean virtual PDFs, perturbed virtual PDFs, and their axes and IDs. The other held-out predictions remain in predictions.csv. Perturbation arrays are indexed (condition, sample, feature); the conditions array omits baseline. PDF values use 2/pi times the trapezoidal integral of Q I(Q) sin(Qr) over the measured angular interval, with wavelength1.5406 Å. distortion.csv gives relative L2 change and retained clean-signal energy for each evaluated example and window. All generated noise draws and fitted models are reproducible from run.py and design.json.

Limitations: one chemistry, one split, one learner family, two hand-chosen artifact families, two severity levels, and three noise draws per level. The broad Gaussian background is a controlled smooth contaminant, not a physical detector-background model. The virtual PDF is uncorrected and should not be interpreted as a quantitatively normalized real-space pair density. The observed selection is conditional on this artifact mixture and the finite angular range.
