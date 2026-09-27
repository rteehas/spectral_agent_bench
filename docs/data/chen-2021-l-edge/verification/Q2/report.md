# Local geometry and L3/L2 spectral weight

At fixed reduced composition the tetrahedral-minus-octahedral log area-ratio contrast is -0.0147 (95% material-bootstrap interval -0.0431 to +0.0020), supported by only 301 sites in 108 materials and 76 element/composition strata. This limited overlap does not establish a composition-invariant geometry effect.

The more broadly supported element-and-ligand-adjusted contrast is -0.0120 (95% material-bootstrap interval -0.0153 to -0.0087); it is negative under the nominal definitions. This contrast uses 4592 sites from 3005 materials in 67 chemistry strata containing both geometries. The paired archive has 13589 sites; geometry counts and element-specific support are reported separately, so the fitted subset is not presented as the whole archive.

Labels are derived from periodic coordinates, never from spectra or file names. A radial first shell at 1.2 times the nearest distance must contain four or six neighbors and meet an angular RMS-cosine distortion tolerance of 0.15 plus radial coefficient of variation <=0.12. Sorted pair cosine patterns distinguish tetrahedral from square-planar CN4 and octahedral from other CN6 arrangements. Sites failing these shape conditions remain other. The finite radius is 6 Å. Tightening/loosening shell ratio to 1.15/1.25 and angular tolerance to 0.10 tests sensitivity. These operational labels favor relatively regular environments; ambiguous or distorted sites are not silently assigned a perfect-polyhedron label.

Each raw spectrum has a nonuniform physical energy grid. We integrate its piecewise-linear cross section from 3 to 33 eV above its first released energy, using the same excess-energy window for both edges. We preserve the supplied absolute relative amplitudes and report ln(area L3 / area L2). Windows 3–23 and 3–43 eV test how the continuum/window definition influences the contrast. The first archived energy is a reproducible FEFF-grid origin, not a measured onset; these are finite-window raw-area ratios, not experimental white-line branching ratios or spin-sum-rule observables. There is no physically justified universal continuum subtraction in these raw arrays, so we do not call the ratio a spin measurement.

We fit weighted linear contrasts with a tetrahedral indicator, standardized mean neighbor distance and absorbing-element atomic fraction. Chemistry fixed effects are first absorbing element, then absorbing element crossed with the set of neighbor species. A further exact reduced-composition fixed-effect comparison holds full elemental stoichiometry constant and reports its smaller overlap population separately. Only chemistry strata containing both shapes support the adjusted geometry coefficient. Multiplicity weights are normalized to give each material total weight one. Confidence intervals resample complete material clusters (400 replicates, fixed seed), refitting all coefficients. Bond length and stoichiometric absorber fraction provide limited chemical/charge proxies; they are not oxidation-state assignments. Ligand identity, element and stoichiometry can still leave residual chemical confounding, so an adjusted association is not causal geometry or spin evidence. Sites of one material are not treated as independent uncertainty units.

associations.csv reports the unadjusted, element-adjusted and element/ligand-adjusted estimates, both alternate windows and all geometry sensitivities. strata.csv displays class coverage by element. Geometry and descriptors are retained for all paired sites; other sites do not enter the binary contrast. The forest plot exposes sign/interval sensitivity without imposing a required positive result. The element/ligand coefficient stays negative over the tested windows and shape choices, while the exact-composition contrast is less precise; the latter prevents treating the broader partial-adjustment association as a universal geometry effect. Element-specific median ratios can have either direction, reinforcing the need to keep pooled and conditional claims distinct. Results are conditional on this archived computational collection, the model's core-hole treatment, finite integration supports and the selected regular-geometry subpopulation.

Numerical contrasts:

```json
[
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry",
    "adjustment": "unadjusted",
    "n_sites": 5408,
    "n_materials": 3602,
    "n_chemical_strata": 1,
    "tetra_minus_octa_log_ratio": -0.003652392956282536,
    "ci025": -0.005304115595115906,
    "ci975": -0.0019464383958978824,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry",
    "adjustment": "element",
    "n_sites": 5408,
    "n_materials": 3602,
    "n_chemical_strata": 8,
    "tetra_minus_octa_log_ratio": -0.004582762103483202,
    "ci025": -0.006264624657687795,
    "ci975": -0.0026569765417407028,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry",
    "adjustment": "element_ligand",
    "n_sites": 4592,
    "n_materials": 3005,
    "n_chemical_strata": 67,
    "tetra_minus_octa_log_ratio": -0.012008932150116697,
    "ci025": -0.015302311406822727,
    "ci975": -0.008676797583906243,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry",
    "adjustment": "exact_composition",
    "n_sites": 301,
    "n_materials": 108,
    "n_chemical_strata": 76,
    "tetra_minus_octa_log_ratio": -0.014671457029415228,
    "ci025": -0.04305356470365392,
    "ci975": 0.002013669208070285,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio_3_23",
    "geometry_definition": "geometry",
    "adjustment": "element_ligand",
    "n_sites": 4592,
    "n_materials": 3005,
    "n_chemical_strata": 67,
    "tetra_minus_octa_log_ratio": -0.015085340893863725,
    "ci025": -0.019201738543176874,
    "ci975": -0.01089607722874184,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio_3_23",
    "geometry_definition": "geometry",
    "adjustment": "exact_composition",
    "n_sites": 301,
    "n_materials": 108,
    "n_chemical_strata": 76,
    "tetra_minus_octa_log_ratio": -0.01653629918125914,
    "ci025": -0.05285432705067774,
    "ci975": 0.004916964751133305,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio_3_43",
    "geometry_definition": "geometry",
    "adjustment": "element_ligand",
    "n_sites": 4592,
    "n_materials": 3005,
    "n_chemical_strata": 67,
    "tetra_minus_octa_log_ratio": -0.009230983702827584,
    "ci025": -0.011842540965678251,
    "ci975": -0.006506082072562653,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio_3_43",
    "geometry_definition": "geometry",
    "adjustment": "exact_composition",
    "n_sites": 301,
    "n_materials": 108,
    "n_chemical_strata": 76,
    "tetra_minus_octa_log_ratio": -0.013159190071778737,
    "ci025": -0.03670260393232647,
    "ci975": 0.00039468582882609964,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_shell_1p15",
    "adjustment": "element_ligand",
    "n_sites": 4413,
    "n_materials": 2909,
    "n_chemical_strata": 73,
    "tetra_minus_octa_log_ratio": -0.0113513455597203,
    "ci025": -0.015241992166354683,
    "ci975": -0.008388473004892831,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_shell_1p15",
    "adjustment": "exact_composition",
    "n_sites": 291,
    "n_materials": 104,
    "n_chemical_strata": 75,
    "tetra_minus_octa_log_ratio": -0.01634504796724049,
    "ci025": -0.04163388629705176,
    "ci975": -0.0003128754570086034,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_shell_1p25",
    "adjustment": "element_ligand",
    "n_sites": 4387,
    "n_materials": 2852,
    "n_chemical_strata": 56,
    "tetra_minus_octa_log_ratio": -0.011695162363908936,
    "ci025": -0.015551735666133753,
    "ci975": -0.008529593253249326,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_shell_1p25",
    "adjustment": "exact_composition",
    "n_sites": 288,
    "n_materials": 100,
    "n_chemical_strata": 72,
    "tetra_minus_octa_log_ratio": -0.010400097026344054,
    "ci025": -0.03867039235289733,
    "ci975": 0.0028779692354173455,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_angular_0p10",
    "adjustment": "element_ligand",
    "n_sites": 3560,
    "n_materials": 2454,
    "n_chemical_strata": 62,
    "tetra_minus_octa_log_ratio": -0.013050412241487742,
    "ci025": -0.016950251140170045,
    "ci975": -0.008847893605339526,
    "bootstrap_replicates": 400
  },
  {
    "feature": "log_ratio",
    "geometry_definition": "geometry_angular_0p10",
    "adjustment": "exact_composition",
    "n_sites": 197,
    "n_materials": 66,
    "n_chemical_strata": 51,
    "tetra_minus_octa_log_ratio": -0.003449450247774963,
    "ci025": -0.03703871045747036,
    "ci975": 0.008799322202912135,
    "bootstrap_replicates": 400
  }
]
```
