# Does local lithium coordination predict a red shift?

These operational definitions do not support a general red shift with increasing lithium coordination. Every fitted partial slope is positive across the three Li cutoffs, three spectral features and pooled/within-material analyses. At the nominal3Å cutoff, the within-material10%-area onset slope is +0.0509eV per Li neighbor (95% block interval -0.0051 to +0.0911); the peak slope is +0.0599 (-0.0348 to +0.1211). Both intervals include zero. Their intervals also include zero at2.8Å but become positive at3.2Å, so evidence for those features is cutoff-dependent.

The within-material centroid slope is +0.2096eV per neighbor (+0.1913 to +0.2218), and its positive interval persists at every tested cutoff. This is an association of larger Li coordination with a higher near-edge centroid, not evidence for shielding-induced red shifts. The centroid summarizes spectral weight across a finite window and need not move like a sharp absorption threshold. Pooled slopes exceed their within-material counterparts, indicating that between-material differences contribute to the pooled pattern. The data and design cannot exclude a red-shift effect under different descriptors or specific chemical subsets.

We treat this as an observational structure–spectrum question. No charge-density or intervention data are supplied, so association cannot establish electronic shielding as the cause. The first core-hole POSCAR atom is the absorbing sulfur. Periodic phosphorus and lithium neighbor counts are derived independently for each site; definitions.json and sites.csv document cutoffs and units.

Peak location, near-edge10%-area energy and centroid probe different notions of an edge shift. All use the same DFT energy reference and Gaussian0.5eV resolution. Regression includes phosphorus coordination. Each material receives equal total regression weight, divided among sites according to symmetry multiplicity. The within-material model demeans outcome and predictors within material, controlling composition and all other material-constant properties. It does not isolate local coordination from other varying bond geometry. The pooled model is a confounding diagnostic. Bootstrap intervals resample66 material blocks200 times and are conditional on this uneven archive, not evidence for population-representative sampling.

Nominal P-coordination counts: {"0": 42, "1": 2589, "2": 50}. Main estimates:
[
  {
    "feature": "onset_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": false,
    "slope_eV_per_Li": 0.09532326867795742,
    "ci025": 0.02701176721728522,
    "ci975": 0.14819161762210814
  },
  {
    "feature": "onset_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": true,
    "slope_eV_per_Li": 0.05087764536576532,
    "ci025": -0.0051032749168470285,
    "ci975": 0.09113994416445455
  },
  {
    "feature": "peak_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": false,
    "slope_eV_per_Li": 0.09600397344036604,
    "ci025": 0.016464785994572413,
    "ci975": 0.16422902979254772
  },
  {
    "feature": "peak_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": true,
    "slope_eV_per_Li": 0.05990667971871068,
    "ci025": -0.034825322245904844,
    "ci975": 0.121057151344712
  },
  {
    "feature": "centroid_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": false,
    "slope_eV_per_Li": 0.2321005492518091,
    "ci025": 0.20484541229102582,
    "ci975": 0.2515377472535816
  },
  {
    "feature": "centroid_e",
    "Li_descriptor": "li_cn",
    "material_fixed_effects": true,
    "slope_eV_per_Li": 0.20957805102696594,
    "ci025": 0.19128493107208966,
    "ci975": 0.22181070176232515
  }
]

Interpret each slope and its interval rather than assigning a universal red-shift rule. associations.csv includes all18 combinations of spectral definition, Li cutoff2.8/3.0/3.2Å, and pooled/within-material model. Effects that change sign or include zero are evidence against a robust general rule under this operational definition. Agreement across definitions would remain observational. The archive is dominated by P coordination1 and related ANN-derived glass models; its66 structures provide substantially fewer independent examples than2681 site spectra.

The finite near-edge window, Gaussian resolution and cutoff convention are chosen analysis assumptions. Peak switching can affect the maximum-energy metric; centroid is an averaged feature rather than an absorption threshold. Lack of absolute experimental alignment does not affect common-origin relative shifts. No experimental validation or causal shielding conclusion is claimed.
