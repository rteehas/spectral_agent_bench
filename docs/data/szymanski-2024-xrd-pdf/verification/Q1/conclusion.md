# Q1: executed controlled baseline

Li-La-Zr-O single: Fused F1=0.9464, exact=0.9464, PDF F1=0.9345, exact=0.9345, XRD F1=0.9107, exact=0.9107.
Li-Ti-P-O single: Fused F1=0.9558, exact=0.9558, PDF F1=0.9503, exact=0.9503, XRD F1=0.9227, exact=0.9227.

Li-La-Zr-O: PDF minus XRD accuracy is +0.0238; fusion minus the better standalone accuracy is +0.0119. There are 8 cases solved by exactly one representation. This establishes partially complementary errors in this fixed within-phase split; averaging scores exploits some of that complementarity.
Li-Ti-P-O: PDF minus XRD accuracy is +0.0276; fusion minus the better standalone accuracy is +0.0055. There are 13 cases solved by exactly one representation. This establishes partially complementary errors in this fixed within-phase split; averaging scores exploits some of that complementarity.

These are controlled ridge/template baselines. Representation and fusion benefits depend on the group; no CNN or historical-score reproduction is claimed.
Splits hold out augmented repeats of already represented phase identities, not unseen phases or experimental materials. Softmax scores are uncalibrated relative scores.
