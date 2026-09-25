# Q5: fixed-holdout research result



Means and standard deviations summarize three random-forest seeds on the same spectral-record split. They measure forest randomness, not uncertainty across new compounds, splits, or experimental spectra.

md: mean maximum-minus-supplied changes in polynomial family importance (a0/a1/a2/a3) are -0.388/+0.328/+0.037/+0.016.

md/poly: normalization changes the score by -0.0459 to +0.0162; importance rank correlations range 0.781–0.907. Cu has the lowest rank stability (score change -0.0328, top-12 overlap 0.263).

md/pointwise: normalization changes the score by -0.0403 to +0.0002; importance rank correlations range 0.279–0.794. Co has the lowest rank stability (score change -0.0403, top-12 overlap 0.000).

coord: mean maximum-minus-supplied changes in polynomial family importance (a0/a1/a2/a3) are -0.029/+0.021/+0.002/+0.009.

coord/poly: normalization changes the score by -0.0305 to +0.0084; importance rank correlations range 0.662–0.848. Cr has the lowest rank stability (score change -0.0171, top-12 overlap 0.412).

coord/pointwise: normalization changes the score by -0.0450 to +0.0142; importance rank correlations range -0.015–0.518. Mn has the lowest rank stability (score change -0.0299, top-12 overlap 0.412).



Ti coord pointwise: max minus supplied normalization macro_f1=-0.0429; importance rank correlation=0.422; top-12 Jaccard=0.333.

Ti coord poly: max minus supplied normalization macro_f1=+0.0040; importance rank correlation=0.733; top-12 Jaccard=0.600.

Ti md pointwise: max minus supplied normalization r2=-0.0321; importance rank correlation=0.395; top-12 Jaccard=0.263.

Ti md poly: max minus supplied normalization r2=-0.0189; importance rank correlation=0.797; top-12 Jaccard=0.263.

V coord pointwise: max minus supplied normalization macro_f1=-0.0181; importance rank correlation=0.518; top-12 Jaccard=0.200.

V coord poly: max minus supplied normalization macro_f1=-0.0158; importance rank correlation=0.740; top-12 Jaccard=0.500.

V md pointwise: max minus supplied normalization r2=-0.0051; importance rank correlation=0.566; top-12 Jaccard=0.500.

V md poly: max minus supplied normalization r2=-0.0016; importance rank correlation=0.907; top-12 Jaccard=0.143.

Cr coord pointwise: max minus supplied normalization macro_f1=-0.0302; importance rank correlation=0.331; top-12 Jaccard=0.091.

Cr coord poly: max minus supplied normalization macro_f1=-0.0171; importance rank correlation=0.662; top-12 Jaccard=0.412.

Cr md pointwise: max minus supplied normalization r2=+0.0002; importance rank correlation=0.643; top-12 Jaccard=0.333.

Cr md poly: max minus supplied normalization r2=+0.0162; importance rank correlation=0.871; top-12 Jaccard=0.412.

Mn coord pointwise: max minus supplied normalization macro_f1=-0.0299; importance rank correlation=-0.015; top-12 Jaccard=0.412.

Mn coord poly: max minus supplied normalization macro_f1=-0.0305; importance rank correlation=0.848; top-12 Jaccard=0.091.

Mn md pointwise: max minus supplied normalization r2=-0.0216; importance rank correlation=0.457; top-12 Jaccard=0.000.

Mn md poly: max minus supplied normalization r2=-0.0191; importance rank correlation=0.822; top-12 Jaccard=0.200.

Fe coord pointwise: max minus supplied normalization macro_f1=-0.0450; importance rank correlation=0.253; top-12 Jaccard=0.000.

Fe coord poly: max minus supplied normalization macro_f1=-0.0268; importance rank correlation=0.800; top-12 Jaccard=0.263.

Fe md pointwise: max minus supplied normalization r2=-0.0077; importance rank correlation=0.294; top-12 Jaccard=0.000.

Fe md poly: max minus supplied normalization r2=-0.0275; importance rank correlation=0.800; top-12 Jaccard=0.091.

Co coord pointwise: max minus supplied normalization macro_f1=+0.0142; importance rank correlation=-0.002; top-12 Jaccard=0.000.

Co coord poly: max minus supplied normalization macro_f1=-0.0071; importance rank correlation=0.812; top-12 Jaccard=0.000.

Co md pointwise: max minus supplied normalization r2=-0.0403; importance rank correlation=0.279; top-12 Jaccard=0.000.

Co md poly: max minus supplied normalization r2=-0.0370; importance rank correlation=0.818; top-12 Jaccard=0.200.

Ni coord pointwise: max minus supplied normalization macro_f1=-0.0336; importance rank correlation=0.446; top-12 Jaccard=0.043.

Ni coord poly: max minus supplied normalization macro_f1=+0.0084; importance rank correlation=0.730; top-12 Jaccard=0.200.

Ni md pointwise: max minus supplied normalization r2=-0.0271; importance rank correlation=0.291; top-12 Jaccard=0.000.

Ni md poly: max minus supplied normalization r2=-0.0459; importance rank correlation=0.813; top-12 Jaccard=0.200.

Cu coord pointwise: max minus supplied normalization macro_f1=-0.0249; importance rank correlation=0.357; top-12 Jaccard=0.000.

Cu coord poly: max minus supplied normalization macro_f1=-0.0131; importance rank correlation=0.728; top-12 Jaccard=0.263.

Cu md pointwise: max minus supplied normalization r2=-0.0319; importance rank correlation=0.794; top-12 Jaccard=0.263.

Cu md poly: max minus supplied normalization r2=-0.0328; importance rank correlation=0.781; top-12 Jaccard=0.263.

Similar prediction scores can coexist with changing attribution. Rank correlation and overlap quantify stability within a representation; correlated features and impurity bias limit causal interpretation.
