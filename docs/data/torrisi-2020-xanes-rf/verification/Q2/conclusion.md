# Q2: fixed-holdout research result



Means and standard deviations summarize three random-forest seeds on the same spectral-record split. They measure forest randomness, not uncertainty across new compounds, splits, or experimental spectra.

Full-spectrum models beat the training-mean baseline MAE for 8/8 elements. High-tail MAE exceeds overall MAE for 8/8; low-tail MAE does so for 7/8.



Ti: R²=0.857, MAE=0.01327 Å (training-mean baseline R²=-0.000, MAE=0.04040 Å). Low/high training-quantile tail MAE=0.03379/0.03103 Å; signed bias=+0.03175/-0.01762 Å (n=56/43 test spectra).

V: R²=0.929, MAE=0.01478 Å (training-mean baseline R²=-0.000, MAE=0.08189 Å). Low/high training-quantile tail MAE=0.00838/0.02313 Å; signed bias=+0.00705/-0.01401 Å (n=64/69 test spectra).

Cr: R²=0.838, MAE=0.01964 Å (training-mean baseline R²=-0.000, MAE=0.10664 Å). Low/high training-quantile tail MAE=0.03071/0.03848 Å; signed bias=+0.02866/-0.01175 Å (n=24/23 test spectra).

Mn: R²=0.919, MAE=0.01671 Å (training-mean baseline R²=-0.000, MAE=0.08865 Å). Low/high training-quantile tail MAE=0.01988/0.03355 Å; signed bias=+0.01769/-0.02438 Å (n=81/79 test spectra).

Fe: R²=0.893, MAE=0.01509 Å (training-mean baseline R²=-0.000, MAE=0.06858 Å). Low/high training-quantile tail MAE=0.02423/0.03064 Å; signed bias=+0.02306/-0.02480 Å (n=62/62 test spectra).

Co: R²=0.911, MAE=0.01641 Å (training-mean baseline R²=-0.000, MAE=0.08822 Å). Low/high training-quantile tail MAE=0.02281/0.05102 Å; signed bias=+0.02163/-0.04725 Å (n=38/29 test spectra).

Ni: R²=0.891, MAE=0.01442 Å (training-mean baseline R²=-0.002, MAE=0.07300 Å). Low/high training-quantile tail MAE=0.02148/0.04052 Å; signed bias=+0.02016/-0.03475 Å (n=42/27 test spectra).

Cu: R²=0.698, MAE=0.04697 Å (training-mean baseline R²=-0.015, MAE=0.09978 Å). Low/high training-quantile tail MAE=0.05786/0.10756 Å; signed bias=+0.05786/-0.10033 Å (n=38/29 test spectra).

Positive low-tail and negative high-tail residuals indicate regression toward common distances where observed. Quantile boundaries were estimated on training labels only.
