# Q3: fixed-holdout research result



Means and standard deviations summarize three random-forest seeds on the same spectral-record split. They measure forest randomness, not uncertainty across new compounds, splits, or experimental spectra.

The full spectrum improves R² over peak position alone for 8/8 elements. The mean paired R² gain is 0.616; the mean MAE reduction is 0.0787 charge units.



Ti: full-spectrum R²=0.571, peak-only R²=0.154; full-spectrum MAE=0.0711, peak-only MAE=0.1052 charge units (training-mean baseline R²=-0.000, MAE=0.1113).

V: full-spectrum R²=0.830, peak-only R²=0.332; full-spectrum MAE=0.0775, peak-only MAE=0.1632 charge units (training-mean baseline R²=-0.000, MAE=0.2051).

Cr: full-spectrum R²=0.847, peak-only R²=0.276; full-spectrum MAE=0.0648, peak-only MAE=0.1659 charge units (training-mean baseline R²=-0.008, MAE=0.1977).

Mn: full-spectrum R²=0.785, peak-only R²=0.234; full-spectrum MAE=0.0622, peak-only MAE=0.1483 charge units (training-mean baseline R²=-0.000, MAE=0.1928).

Fe: full-spectrum R²=0.790, peak-only R²=0.045; full-spectrum MAE=0.0920, peak-only MAE=0.2014 charge units (training-mean baseline R²=-0.001, MAE=0.2099).

Co: full-spectrum R²=0.820, peak-only R²=0.017; full-spectrum MAE=0.0658, peak-only MAE=0.1511 charge units (training-mean baseline R²=-0.018, MAE=0.1522).

Ni: full-spectrum R²=0.606, peak-only R²=-0.103; full-spectrum MAE=0.0606, peak-only MAE=0.1013 charge units (training-mean baseline R²=-0.008, MAE=0.0967).

Cu: full-spectrum R²=0.682, peak-only R²=0.047; full-spectrum MAE=0.0848, peak-only MAE=0.1715 charge units (training-mean baseline R²=-0.007, MAE=0.1752).

The paired full-versus-peak comparison estimates additional predictive information under this model and holdout. It is not a causal test or a measurement of formal oxidation states.
