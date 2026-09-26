# Site treatment and material fingerprints

Site-specific excitation alignment is consequential across this collection. At Gaussian FWHM0.5eV, replacing relative site shifts by one material-average shift changes normalized shape by a median 12.8% and up to 41.5% (material 066). At1eV the median falls to 5.8%, but the largest effect remains 25.6%, again in material 066. Finite resolution therefore weakens the typical effect without making relative alignment generally dispensable.

Equal weighting has a zero median effect because most materials have equal multiplicity ratios. Its largest0.5eV shape error is 5.1% in material 044; at1eV the maximum is 5.7% in material 059. Those exceptions preclude treating zero median distortion as a universal simplification. effects.csv identifies the material-dependent cases. This analysis quantifies within-material treatment sensitivity; it does not establish preservation of pairwise material similarity rankings under either simplification.

The recovered powder response uses the diagonal mean, excitation-energy alignment and symmetry ratios. The neutral and core-hole cells have the same atom count here; the implementation checks their ratio. The energy axis has a common DFT zero and is not calibrated to experiment. bulk.npz contains all66 native-resolution material responses, with keys m001..m066 and energy/intensity columns.

I tested two counterfactuals: replacing each site's correction by its within-material weighted mean, and giving inequivalent sites equal weights. The first preserves the material mean shift and isolates relative alignment; the second isolates population weighting. Cubic interpolation and zero extension reconstruct the native material responses. Each comparison is peak-normalized and evaluated over the complete released energy support. effects.csv retains every material and resolution, and ablations.npz records energy/full/common-shift/equal-weight columns.

Results:
{
  "common_site_shift_0.0": {
    "median_relative_L2": 0.3072487569850085,
    "maximum_relative_L2": 0.6568499352038507,
    "max_material": "021"
  },
  "common_site_shift_0.5": {
    "median_relative_L2": 0.1282246811528252,
    "maximum_relative_L2": 0.4147026854110275,
    "max_material": "066"
  },
  "common_site_shift_1.0": {
    "median_relative_L2": 0.05764677198063334,
    "maximum_relative_L2": 0.25639367170454014,
    "max_material": "066"
  },
  "equal_site_weights_0.0": {
    "median_relative_L2": 2.822094471894942e-16,
    "maximum_relative_L2": 0.14502209905227456,
    "max_material": "059"
  },
  "equal_site_weights_0.5": {
    "median_relative_L2": 1.5849489918311692e-16,
    "maximum_relative_L2": 0.05149118346864847,
    "max_material": "044"
  },
  "equal_site_weights_1.0": {
    "median_relative_L2": 1.5039511318304742e-16,
    "maximum_relative_L2": 0.057281621576184695,
    "max_material": "059"
  }
}

Relative alignment can alter shapes even when the bulk energy zero is held fixed. Multiplicity matters only when the supplied ratios differ; a zero effect for equal-ratio materials is an exact control, not evidence that multiplicity is generally dispensable. Broader features can attenuate some differences but do not justify interchangeable-site assumptions for every structure. The overlays show representative site-population cases, not an experimental validation.

Resolution sensitivity is tested with Gaussian FWHM0,0.5,1eV. These are controlled examples, not a fit of instrumental/core-hole broadening. Neither stochastic confidence intervals nor population extrapolation are warranted for this complete fixed collection. Interpolation and resolution choices, unknown experimental calibration, finite archived spectral ranges and absence of measured targets limit the conclusions. An independent evaluator may compare bulk.npz with the authors' held-back raw averages; they were not loaded in this computation.
