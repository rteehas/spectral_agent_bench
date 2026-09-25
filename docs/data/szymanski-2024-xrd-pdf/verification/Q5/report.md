# Can a different representation separate weak structure from nuisance?

**Status of this worked investigation.** The author already knew the virtual-PDF idea. This execution demonstrates one admissible evidence-building workflow; it is not evidence that an investigator or agent independently discovered that idea. Naming a transform alone is not the scientific result.

**Initial hypotheses.** Strong peaks may dominate similarity while weak peaks distinguish otherwise similar phases. Intensity compression could expose those weak distinctions, but may also amplify weak noise and background. A second hypothesis is that broad smooth background occupies a separable part of a physically defined representation. I compare raw intensities, signed square-root compression, broad-background subtraction, a smoothed derivative, and several windows of a Q-weighted sine transform. All alternatives use the same ridge classifier family so that classifier choice is not the explanation for differences.

**Physical construction and numerical choices.** Interpolate to 2,001 angle samples over 10.02–79.98 degrees, subtract each spectrum's tenth percentile and divide by its peak, retaining negative residuals. Use unit L2 feature normalization. With wavelength 1.5406 Å and theta half the recorded two-theta angle, define Q=4pi sin(theta)/lambda and G(r)=(2/pi) integral Q I(Q) sin(Qr)dQ. The quadrature uses the actual nonuniform Q spacings. The sine basis connects scattering-vector variation to real-space distance, but the absent physical corrections mean G is a virtual, uncorrected PDF. A background varying slowly in Q is expected mainly at short distances, while sharper diffraction structure can survive at larger distances; Q weighting also changes the relative influence of angular regions. Finite support can leak artifacts across windows, so this physical argument needs numerical checking. It is evaluated at 1,191 distances over 1–120 Å; windows 1–5, 5–40, 1–40, and 40–120 Å test localization and signal loss. Angular truncation deliberately limits this baseline; higher-angle data and other preprocessing choices are not explored.

**Separation of selection from evaluation.** Phase-stratified training, validation and test repeats are disjoint. Templates and nearest-phase hypotheses use training only. Each candidate classifier is trained on clean released training spectra; regularization and representation are selected using clean/noise/background validation performance, giving the three artifact families equal weight. Synthetic artifacts are independently generated for validation and test. Here clean means no additional corruption; the release already includes simulated artifacts. After selection, all alternatives are evaluated on the same held-out spectra. Test labels are used only for scoring and interpretation.

## Li-La-Zr-O

**Training evidence.** The closest training-template pair is ZrO2_225 / ZrO2_61, raw cosine similarity 0.9485. Regions where both templates are below 20% peak occupy 96.3% of sampled angles but contain 36.7% of their squared difference. This measures the actual support for the weak-feature hypothesis; low energy here would limit that explanation. The corresponding feature-space similarities for all alternatives and the three closest pairs are in training_pair_diagnostics.csv.
Clean raw-XRD validation confusions (up to five): [(('Zr3O_182', 'Zr3O_167'), 1), (('Zr2O_224', 'ZrO2_225'), 1), (('ZrO2_225', 'ZrO2_61'), 1)].
**Direct reliance diagnostic.** Setting the strongest 10% of angular channels in each validation spectrum to zero changes raw-XRD accuracy by -0.902; removing the weakest 10% changes it by +0.000; removing a matched random 10% changes it by -0.007 on average across 20 draws. Masks depend only on observed intensity, never the phase label; the fixed classifier is rescored after feature normalization. This artificial deletion intervention tests reliance on intense channels more directly than template similarity does. It also removes physical information, so it cannot by itself establish that such reliance is excessive or that compression should help.
**Selection before test.** PDF 5–40 Å was selected with balanced validation accuracy 0.983. All validation scores and alpha searches are in design.json; no method is assumed to win because of its name.

Raw XRD: validation balanced 0.962; held-out clean/noise/background accuracy 0.955/0.951/0.902.
Signed sqrt: validation balanced 0.943; held-out clean/noise/background accuracy 0.946/0.946/0.897.
Background subtraction: validation balanced 0.973; held-out clean/noise/background accuracy 0.955/0.954/0.955.
Smoothed derivative: validation balanced 0.857; held-out clean/noise/background accuracy 0.857/0.868/0.857.
PDF 1–5 Å: validation balanced 0.550; held-out clean/noise/background accuracy 0.750/0.707/0.147.
PDF 5–40 Å: validation balanced 0.983; held-out clean/noise/background accuracy 0.964/0.964/0.964.
PDF 1–40 Å: validation balanced 0.952; held-out clean/noise/background accuracy 0.955/0.955/0.911.
PDF 40–120 Å: validation balanced 0.835; held-out clean/noise/background accuracy 0.857/0.847/0.857.

Selected-method minus raw-XRD accuracy for clean: +0.009, phase-block bootstrap 95% interval [-0.018,+0.045].
Selected-method minus raw-XRD accuracy for noise: +0.013, phase-block bootstrap 95% interval [-0.010,+0.042].
Selected-method minus raw-XRD accuracy for background: +0.062, phase-block bootstrap 95% interval [+0.009,+0.125].
The best validation-selected virtual-PDF window is PDF 5–40 Å, and the best non-PDF alternative is Background subtraction. Their held-out background accuracies are 0.964 and0.955, respectively. Thus the physical transform must be judged against an effective simpler competitor, not only against untreated intensities.

Validation-selected PDF minus validation-selected non-PDF accuracy for clean: +0.009, phase-block 95% interval [-0.018, +0.045].
Validation-selected PDF minus validation-selected non-PDF accuracy for noise: +0.010, phase-block 95% interval [-0.012, +0.039].
Validation-selected PDF minus validation-selected non-PDF accuracy for background: +0.009, phase-block 95% interval [-0.018, +0.045].
The selected PDF window retains 51.6% of sampled clean-signal energy but only 0.015% of added smooth-background energy on validation spectra. Together with its held-out background result, this supports the nuisance-localization mechanism for these constructed backgrounds. Signed square-root compression changes held-out clean accuracy by -0.009 relative to raw XRD; the weak-feature hypothesis does not by itself justify compression as an effective remedy.
Clean selected-method held-out confusions (up to five): [(('ZrO2_225', 'Zr2O_224'), 2), (('ZrO2_61', 'Zr2O_224'), 1), (('Li7La3Zr2O12_230', 'Li7La3Zr2O12_142'), 1)]. These were inspected only after final selection; confusion_counts.csv retains every condition and method.

## Li-Ti-P-O

**Training evidence.** The closest training-template pair is LiTi2O4_11 / LiTi2O4_58, raw cosine similarity 0.9815. Regions where both templates are below 20% peak occupy 93.9% of sampled angles but contain 33.5% of their squared difference. This measures the actual support for the weak-feature hypothesis; low energy here would limit that explanation. The corresponding feature-space similarities for all alternatives and the three closest pairs are in training_pair_diagnostics.csv.
Clean raw-XRD validation confusions (up to five): [(('LiTi2O4_11', 'LiTi2O4_58'), 1), (('LiTi2O4_11', 'LiTi2O4_31'), 1), (('LiPO3_13', 'TiP2O7_205'), 1), (('LiTi2(PO4)3_167', 'Li2Ti2(PO4)3_60'), 1)].
**Direct reliance diagnostic.** Setting the strongest 10% of angular channels in each validation spectrum to zero changes raw-XRD accuracy by -0.885; removing the weakest 10% changes it by +0.000; removing a matched random 10% changes it by +0.002 on average across 20 draws. Masks depend only on observed intensity, never the phase label; the fixed classifier is rescored after feature normalization. This artificial deletion intervention tests reliance on intense channels more directly than template similarity does. It also removes physical information, so it cannot by itself establish that such reliance is excessive or that compression should help.
**Selection before test.** PDF 5–40 Å was selected with balanced validation accuracy 0.974. All validation scores and alpha searches are in design.json; no method is assumed to win because of its name.

Raw XRD: validation balanced 0.937; held-out clean/noise/background accuracy 0.945/0.945/0.900.
Signed sqrt: validation balanced 0.908; held-out clean/noise/background accuracy 0.931/0.932/0.824.
Background subtraction: validation balanced 0.943; held-out clean/noise/background accuracy 0.931/0.938/0.934.
Smoothed derivative: validation balanced 0.880; held-out clean/noise/background accuracy 0.883/0.864/0.883.
PDF 1–5 Å: validation balanced 0.486; held-out clean/noise/background accuracy 0.641/0.618/0.097.
PDF 5–40 Å: validation balanced 0.974; held-out clean/noise/background accuracy 0.945/0.947/0.941.
PDF 1–40 Å: validation balanced 0.921; held-out clean/noise/background accuracy 0.890/0.890/0.838.
PDF 40–120 Å: validation balanced 0.873; held-out clean/noise/background accuracy 0.848/0.849/0.848.

Selected-method minus raw-XRD accuracy for clean: +0.000, phase-block bootstrap 95% interval [-0.027,+0.027].
Selected-method minus raw-XRD accuracy for noise: +0.002, phase-block bootstrap 95% interval [-0.022,+0.026].
Selected-method minus raw-XRD accuracy for background: +0.041, phase-block bootstrap 95% interval [+0.007,+0.081].
The best validation-selected virtual-PDF window is PDF 5–40 Å, and the best non-PDF alternative is Background subtraction. Their held-out background accuracies are 0.941 and0.934, respectively. Thus the physical transform must be judged against an effective simpler competitor, not only against untreated intensities.

Validation-selected PDF minus validation-selected non-PDF accuracy for clean: +0.014, phase-block 95% interval [-0.013, +0.041].
Validation-selected PDF minus validation-selected non-PDF accuracy for noise: +0.009, phase-block 95% interval [-0.010, +0.030].
Validation-selected PDF minus validation-selected non-PDF accuracy for background: +0.007, phase-block 95% interval [-0.014, +0.028].
The selected PDF window retains 52.5% of sampled clean-signal energy but only 0.015% of added smooth-background energy on validation spectra. Together with its held-out background result, this supports the nuisance-localization mechanism for these constructed backgrounds. Signed square-root compression changes held-out clean accuracy by -0.014 relative to raw XRD; the weak-feature hypothesis does not by itself justify compression as an effective remedy.
Clean selected-method held-out confusions (up to five): [(('LiTiO2_227', 'LiTi2O4_227'), 3), (('Li4Ti5O12_227', 'Li2TiO3_15'), 2), (('LiTiPO5_62', 'Ti5(PO5)4_19'), 1), (('Li4Ti5O12_227', 'LiTiO2_227'), 1), (('LiTi2O4_11', 'LiTi2O4_58'), 1)]. These were inspected only after final selection; confusion_counts.csv retains every condition and method.

## What the experiment supports

The validation-selected method improves background-corrupted accuracy over raw XRD with a positive paired interval in 2 of 2 chemistries. Against the validation-selected non-PDF competitor, the best PDF window has a positive background-accuracy interval in 0 of 2 chemistries. The principal evidence concerns smooth-background robustness. Small clean/noise differences must be read with their intervals and do not establish a broad superiority claim. Removing intense channels confirms that raw classification relies on them, but weaker performance after compression shows why reliance alone is not a diagnosis of avoidable error.

The physically defined transform and a distance-window search constitute an implemented representation proposal. Whether that proposal is useful is a separate empirical claim: use the held-out comparisons above, including the non-PDF alternatives and the paired uncertainty. Signed compression, high-pass filtering and derivatives test competing explanations for any gain. Training-template differences test whether weak intensities actually distinguish near-neighbor phases; validation artifact-energy localization tests the proposed separation mechanism. Neither diagnostic alone proves an accuracy improvement. The classification results are the functional check.

The saved validation_localization.csv quantifies smooth-background/noise energy and retained signal in each distance window. The eigenstructure of the finite sampled transform and truncation matter: this is an information reweighting and filtering experiment, not creation of new information. A useful window can suppress background while retaining enough phase distinction, but it can also discard discriminative signal. A representation that loses to a simpler alternative still provides a valid negative finding.

## Uncertainty, limitations and reproducibility

Paired confidence intervals use 2,000 bootstrap resamples of phase identities, carrying their repeated test spectra together. Condition severities and noise draws are averaged within each spectrum before resampling. The intervals condition on one training/validation split and do not include selection or retraining uncertainty. Boundary empirical intervals may collapse and do not establish certainty for future specimens. The benchmark tests augmented repeats of represented structures, not unseen phases or measured specimens. Synthetic Gaussian noise and broad backgrounds span only two severities and are controlled mechanisms, not comprehensive instrument models. All methods use one learner family and modest searches; this does not establish universal representation superiority or a global optimum.

predictions.csv, splits.csv and conditions.csv allow independent label-based scoring. metrics.csv is a convenience summary; uncertainty.json records paired contrasts. design.json records all validation searches and selections. evidence.npz saves the first 12 held-out IDs per chemistry, their clean/perturbed preprocessed XRD, corresponding full 1–120 Å virtual PDFs, and axes. Perturbed arrays have axes(condition,sample,feature), with baseline omitted from the condition list. Additional ablation_ids and ablation_clean_xrd contain twelve validation records per chemistry; ablation_strong_masks and ablation_weak_masks are(sample,angle), and ablation_random_masks is(draw,sample,angle). A true mask entry sets that observed intensity to zero. validation_ablation.csv retains full-validation accuracy and true-class decision-margin changes. These audit IDs were fixed before examining outcomes; all spectra were evaluated. run.py reconstructs every generated array and result using only the supplied four raw input files.
