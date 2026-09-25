# Q1: fixed-holdout research result



Means and standard deviations summarize three random-forest seeds on the same spectral-record split. They measure forest randomness, not uncertainty across new compounds, splits, or experimental spectra.

Balanced spectral models exceed the training-mode accuracy baseline for 8/8 elements. Oversampling improves macro-F1 for 4/8 elements, with mean paired change +0.0150.



Ti: training minority class CN=4; balanced accuracy 0.873 versus mode baseline 0.514; minority F1 0.816; oversampling changes macro-F1 by -0.0011.

V: training minority class CN=4; balanced accuracy 0.879 versus mode baseline 0.383; minority F1 0.961; oversampling changes macro-F1 by -0.0002.

Cr: training minority class CN=4; balanced accuracy 0.865 versus mode baseline 0.591; minority F1 0.939; oversampling changes macro-F1 by +0.0164.

Mn: training minority class CN=4; balanced accuracy 0.807 versus mode baseline 0.496; minority F1 0.592; oversampling changes macro-F1 by +0.0514.

Fe: training minority class CN=4; balanced accuracy 0.840 versus mode baseline 0.463; minority F1 0.835; oversampling changes macro-F1 by -0.0027.

Co: training minority class CN=4; balanced accuracy 0.811 versus mode baseline 0.526; minority F1 0.807; oversampling changes macro-F1 by -0.0063.

Ni: training minority class CN=4; balanced accuracy 0.890 versus mode baseline 0.671; minority F1 0.840; oversampling changes macro-F1 by +0.0177.

Cu: training minority class CN=4; balanced accuracy 0.853 versus mode baseline 0.678; minority F1 0.632; oversampling changes macro-F1 by +0.0452.

Assess minority-class F1 and confusion together: a high total accuracy alone does not establish balanced class resolution. Oversampling benefits are element dependent.
