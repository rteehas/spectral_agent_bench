# Inequivalent sites and material fingerprints

Reconstruction yields 15792 complete material/element/edge responses and excludes 386 groups. At 1 eV Gaussian FWHM, equal-site averaging has median shape error 0.00% and 95th percentile 6.54% among 5191 complete multisite edge responses. Choosing the lowest-index representative has median 5.67% and 95th percentile 28.05%. The fractions exceeding 5% are 7.61% and 55.15%, respectively. Thus the validity of either simplification is material dependent; a small median does not validate it in every material.

The symmetry equivalence classes and their atom counts come from the released periodic structure using spglib (0.01 Å, 5 degrees). Each included edge must contain one valid record for every equivalence class of its absorbing element. Multiplicities are normalized only after this completeness test. We do not silently renormalize a partial set into a complete response. coverage.csv and sites.csv retain all records and exclusions. Symmetry-failure groups are excluded. Physical lattice/coordinates/species equality is audited; optional metadata differences do not invalidate a structure, while all records of a conflicting structure identifier are excluded. Symmetry tolerances 0.001 and 0.1 Å are re-evaluated in symmetry_sensitivity.csv, including coverage and multiplicity changes. L2 and L3 are reconstructed separately at their physical photon energies; their finite energy ranges need not overlap, so an unmeasured zero-filled combined spectrum is not manufactured.

responses.npz stores energy/intensity columns on the union of native knots restricted to the intersection of all included site's supports. This is an exact piecewise-linear population average on measured support. No edge is individually normalized before averaging. The equal-site ablation changes only population weights; the representative ablation takes the lowest-index absorbing site, an explicit arbitrary site-choice rule. ablations.npz stores energy/full/equal/representative columns.

The shape metric compares area-normalized spectra on a 0.1 eV grid after a controlled Gaussian FWHM 0, 1 or 2 eV convolution; the first and last 3 eV are excluded to reduce boundary-extension effects. Amplitude error and peak displacement are also retained in effects.csv. Single-site groups are exact zero-effect controls and excluded from the sensitivity distribution so they cannot dilute the multisite question. Equal multiplicities likewise force exact equal-site invariance. We show extreme representative failures rather than selecting visually appealing average cases.

The collection is fixed, so these are descriptive distributions rather than sampling-population confidence intervals. Broadening experiments test finite-resolution robustness; they do not fit an experimental instrument. For each approximation, ranking_sensitivity.csv ranks materials by their largest edge/element shape distortion and compares 1/2 eV with unbroadened spectra using Spearman correlation and top-50 overlap. This directly tests whether resolution changes the high-risk material list. The arbitrary representative rule does not show that every possible chosen site is equally poor. Absolute FEFF amplitudes, symmetry tolerance, support truncation and the dataset's chemical selection bound the conclusions. Geometry and magnetic/spin populations are not inferred from these reconstructions.

Full numerical summary:

```json
{
  "raw_records": 27570,
  "complete_responses": 15792,
  "excluded_responses": 386,
  "exclusion_reasons": {
    "incomplete_symmetry_coverage": 335,
    "invalid_spectrum": 44,
    "incomplete_symmetry_coverage;invalid_spectrum": 1,
    "inconsistent_structure": 2,
    "incomplete_symmetry_coverage;duplicate_symmetry_class;inconsistent_structure": 2,
    "duplicate_symmetry_class": 2
  },
  "symmetry_sensitivity": {
    "0.001": {
      "changed_equivalence_groups": 880,
      "changed_multiplicity_records": 1154
    },
    "0.1": {
      "changed_equivalence_groups": 536,
      "changed_multiplicity_records": 1738
    }
  },
  "statistics": [
    {
      "approximation": "equal_sites",
      "fwhm_eV": 0.0,
      "n_multisite_responses": 5191,
      "median": 1.3427835386388687e-16,
      "q95": 0.08294241431850577,
      "max": 0.5697476649209825,
      "fraction_over_5pct": 0.11173184357541899,
      "worst_material": "mp-505018",
      "worst_element": "Mn",
      "worst_edge": "L3"
    },
    {
      "approximation": "equal_sites",
      "fwhm_eV": 1.0,
      "n_multisite_responses": 5191,
      "median": 1.2961072111349291e-16,
      "q95": 0.06541131668587037,
      "max": 0.3517632731256017,
      "fraction_over_5pct": 0.07609323829705258,
      "worst_material": "mp-505018",
      "worst_element": "Mn",
      "worst_edge": "L3"
    },
    {
      "approximation": "equal_sites",
      "fwhm_eV": 2.0,
      "n_multisite_responses": 5191,
      "median": 1.3137331147185944e-16,
      "q95": 0.047747826399478485,
      "max": 0.21465748237342439,
      "fraction_over_5pct": 0.047004430745521096,
      "worst_material": "mp-653429",
      "worst_element": "Mn",
      "worst_edge": "L3"
    },
    {
      "approximation": "first_representative",
      "fwhm_eV": 0.0,
      "n_multisite_responses": 5191,
      "median": 0.07387190537036736,
      "q95": 0.354534187712349,
      "max": 0.8507789229907279,
      "fraction_over_5pct": 0.6544018493546523,
      "worst_material": "mp-1194593",
      "worst_element": "V",
      "worst_edge": "L3"
    },
    {
      "approximation": "first_representative",
      "fwhm_eV": 1.0,
      "n_multisite_responses": 5191,
      "median": 0.05665118252927267,
      "q95": 0.28053012507868025,
      "max": 0.8573625073455169,
      "fraction_over_5pct": 0.5515314968214217,
      "worst_material": "mp-615152",
      "worst_element": "Mn",
      "worst_edge": "L3"
    },
    {
      "approximation": "first_representative",
      "fwhm_eV": 2.0,
      "n_multisite_responses": 5191,
      "median": 0.04279311061969044,
      "q95": 0.21769914139034546,
      "max": 0.8293485473539121,
      "fraction_over_5pct": 0.4301675977653631,
      "worst_material": "mp-615152",
      "worst_element": "Mn",
      "worst_edge": "L3"
    }
  ],
  "resolution_rank_stability": [
    {
      "approximation": "equal_sites",
      "fwhm_eV": 1.0,
      "n_materials": 2576,
      "spearman_vs_unbroadened": 0.9950229613052464,
      "top50_overlap": 45,
      "top50_jaccard": 0.8181818181818182,
      "worst_material": "mp-505018"
    },
    {
      "approximation": "equal_sites",
      "fwhm_eV": 2.0,
      "n_materials": 2576,
      "spearman_vs_unbroadened": 0.9864523523445107,
      "top50_overlap": 40,
      "top50_jaccard": 0.6666666666666666,
      "worst_material": "mp-653429"
    },
    {
      "approximation": "first_representative",
      "fwhm_eV": 1.0,
      "n_materials": 2576,
      "spearman_vs_unbroadened": 0.955518766606502,
      "top50_overlap": 35,
      "top50_jaccard": 0.5384615384615384,
      "worst_material": "mp-615152"
    },
    {
      "approximation": "first_representative",
      "fwhm_eV": 2.0,
      "n_materials": 2576,
      "spearman_vs_unbroadened": 0.8750521772967351,
      "top50_overlap": 31,
      "top50_jaccard": 0.4492753623188406,
      "worst_material": "mp-615152"
    }
  ]
}
```
