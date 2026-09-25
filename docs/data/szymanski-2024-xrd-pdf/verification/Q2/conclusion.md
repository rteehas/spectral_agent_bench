# Q2: executed controlled baseline

Li-La-Zr-O 2-Phase: Fused F1=0.8950, exact=0.7950, PDF F1=0.8962, exact=0.8000, XRD F1=0.8738, exact=0.7625.
Li-La-Zr-O 3-Phase: Fused F1=0.7692, exact=0.3925, PDF F1=0.7650, exact=0.3975, XRD F1=0.7583, exact=0.3700.
Li-Ti-P-O 2-Phase: Fused F1=0.9175, exact=0.8400, PDF F1=0.9113, exact=0.8325, XRD F1=0.9075, exact=0.8200.
Li-Ti-P-O 3-Phase: Fused F1=0.7858, exact=0.4125, PDF F1=0.7742, exact=0.3925, XRD F1=0.7642, exact=0.3750.

Li-La-Zr-O, XRD: from two to three constituents, micro-F1 changes -0.1154 and exact recovery changes -0.3925.
Li-La-Zr-O, PDF: from two to three constituents, micro-F1 changes -0.1312 and exact recovery changes -0.4025.
Li-La-Zr-O, Fused: from two to three constituents, micro-F1 changes -0.1258 and exact recovery changes -0.4025.
The larger loss in complete phase-set recovery shows why high average constituent recall can conceal unsuccessful mixture identification. These are different mixtures at each cardinality, so composition and abundance differences may also contribute; this is not a pure causal isolation of peak overlap.
Li-Ti-P-O, XRD: from two to three constituents, micro-F1 changes -0.1433 and exact recovery changes -0.4450.
Li-Ti-P-O, PDF: from two to three constituents, micro-F1 changes -0.1371 and exact recovery changes -0.4400.
Li-Ti-P-O, Fused: from two to three constituents, micro-F1 changes -0.1317 and exact recovery changes -0.4275.
The larger loss in complete phase-set recovery shows why high average constituent recall can conceal unsuccessful mixture identification. These are different mixtures at each cardinality, so composition and abundance differences may also contribute; this is not a pure causal isolation of peak overlap.

These are controlled ridge/template baselines. Representation and fusion benefits depend on the group; no CNN or historical-score reproduction is claimed.
The true number of phases is supplied. Exact phase-set recovery is stricter than micro F1. Coefficients measure spectral contribution, not mass fraction. Ordered duplicates of phase combinations remain separate measured/simulated patterns; they are not independent material families.
