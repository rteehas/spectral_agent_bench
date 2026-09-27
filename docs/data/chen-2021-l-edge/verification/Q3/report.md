# Does L2 improve coordination prediction on unseen compositions?

On 5408 regularly tetrahedral or octahedral sites from 3602 materials and 3339 reduced compositions, adding L2 changes composition-held-out balanced accuracy by +0.0022, with a paired 95% composition-bootstrap interval -0.0008 to +0.0057. This does not resolve an incremental benefit from zero for the fixed model and operational labels. The broadened comparison is independently reported below, and the element-prior control exposes the accuracy available from class/chemistry imbalance alone.

Periodic geometry labels use the same explicit nearest-shell and ideal angular-shape test recorded in definitions.json and geometry.csv. Square-planar CN4 does not pass the tetrahedral criterion. Other/ambiguous geometry and missing/invalid paired spectra are excluded with reasons in exhaustive sites.csv. Both spectral models see exactly the same paired sites, labels, train/test compositions and seed. Four shuffled stratified-group folds hold out the canonical reduced elemental composition, so polymorphs and multiple sites of a formula cannot cross train/test partitions. partitions.csv declares every material's training/test role for each method/fold; every eligible site has one OOF prediction per method.

Features are linearly interpolated raw intensities sampled on 3:0.5:43 eV above each edge's first archived energy. L3 is area-normalized; in the combined model both edges are divided by that same L3 area, preserving relative L2/L3 intensity. This removes overall amplitude while retaining the added edge's shape and relative weight. No element, formula, MP ID, structure or geometry descriptor enters either spectral classifier. The only chemistry-feature predictor is the explicitly labeled element-prior control, not a spectral model. It and the global-majority control fit only training labels. Nonuniform native array indices are never treated as a uniform energy axis.

Random forests use 240 trees, balanced-subsample class weights, minimum leaf size 2 and square-root feature subsampling, fixed in advance without tuning on held-out labels. This model comparison establishes achievable information for one transparent model, not the Bayes-optimal value of L2. Repeating the entire matched comparison at Gaussian FWHM 1 eV tests loss of resolution. We also evaluate unchanged OOF predictions on the subset retaining geometry labels under shell ratios 1.15 and 1.25; that is a label-stability sensitivity, not a retraining experiment.

Balanced accuracy, macro F1, ordered confusion matrices and per-element support/accuracy expose class imbalance. The nominal per-element L2 increments range from -0.0033 to +0.0143; element_metrics.csv and the per-element summary retain all class counts and point differences. These are descriptive chemical heterogeneity checks, not eight independent claims of significance, and the smallest classes provide weaker evidence. Uncertainty uses 500 resamples of reduced-composition groups from the fixed OOF predictions; identical resamples yield paired differences. These intervals reflect test-composition variation conditional on the fitted folds, not training/model-selection variability. No random site split or site-independent confidence interval is used. Composition holdout does not by itself test transfer to new elements, ligands, experimental noise, uncertain energy alignment or experimental spectra. FEFF approximations and the narrow regular-geometry label subset limit external interpretation; predictive success cannot imply spin or oxidation-state determination.

Full quantitative results:

```json
{
  "n_sites": 5408,
  "n_materials": 3602,
  "n_compositions": 3339,
  "class_counts": {
    "tetrahedral": 1722,
    "octahedral": 3686
  },
  "classes_confusion_order": [
    "octahedral",
    "tetrahedral"
  ],
  "bootstrap_replicates": 500,
  "metrics": [
    {
      "method": "L3_fwhm0",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.9571894596939923,
      "macro_f1": 0.9595338669764244,
      "ci025": 0.949847111226453,
      "ci975": 0.9643485059576181,
      "confusion_matrix": [
        [
          3608,
          78
        ],
        [
          111,
          1611
        ]
      ]
    },
    {
      "method": "L23_fwhm0",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.9593576284185446,
      "macro_f1": 0.9612833964266738,
      "ci025": 0.9521386717793616,
      "ci975": 0.9659527480083246,
      "confusion_matrix": [
        [
          3609,
          77
        ],
        [
          104,
          1618
        ]
      ]
    },
    {
      "method": "L3_fwhm1",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.9613901487437477,
      "macro_f1": 0.9628216409758465,
      "ci025": 0.9543597000423371,
      "ci975": 0.9679967355999878,
      "confusion_matrix": [
        [
          3609,
          77
        ],
        [
          97,
          1625
        ]
      ]
    },
    {
      "method": "L23_fwhm1",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.9628228857282759,
      "macro_f1": 0.9641148994357406,
      "ci025": 0.9553614721892612,
      "ci975": 0.9692993837342412,
      "confusion_matrix": [
        [
          3611,
          75
        ],
        [
          93,
          1629
        ]
      ]
    },
    {
      "method": "majority",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.5,
      "macro_f1": 0.4053221904552452,
      "ci025": 0.5,
      "ci975": 0.5,
      "confusion_matrix": [
        [
          3686,
          0
        ],
        [
          1722,
          0
        ]
      ]
    },
    {
      "method": "element_prior",
      "n_test_sites": 5408,
      "balanced_accuracy": 0.6799995966783945,
      "macro_f1": 0.6914139653770187,
      "ci025": 0.659753800162044,
      "ci975": 0.6998984629065979,
      "confusion_matrix": [
        [
          3262,
          424
        ],
        [
          904,
          818
        ]
      ]
    }
  ],
  "paired_differences": [
    {
      "fwhm_eV": 0.0,
      "L23_minus_L3_balanced_accuracy": 0.0021681687245522774,
      "ci025": -0.0007585139814401231,
      "ci975": 0.005741398519828563
    },
    {
      "fwhm_eV": 1.0,
      "L23_minus_L3_balanced_accuracy": 0.0014327369845281712,
      "ci025": -0.0014660364877833064,
      "ci975": 0.004545337179305047
    }
  ],
  "label_stability_subset": [
    {
      "method": "L3_fwhm0",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.9566972150290242
    },
    {
      "method": "L23_fwhm0",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.9586097330022956
    },
    {
      "method": "L3_fwhm1",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.9615763620085958
    },
    {
      "method": "L23_fwhm1",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.962123436445725
    },
    {
      "method": "majority",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.5
    },
    {
      "method": "element_prior",
      "n_stable_sites": 4635,
      "balanced_accuracy": 0.7036583866369002
    }
  ],
  "per_element_differences": [
    {
      "element": "Ti",
      "n_tetrahedral": 41,
      "n_octahedral": 478,
      "L23_minus_L3_balanced_accuracy": 0.014287172160424522
    },
    {
      "element": "V",
      "n_tetrahedral": 482,
      "n_octahedral": 315,
      "L23_minus_L3_balanced_accuracy": 0.0
    },
    {
      "element": "Cr",
      "n_tetrahedral": 215,
      "n_octahedral": 346,
      "L23_minus_L3_balanced_accuracy": 0.0046511627906977715
    },
    {
      "element": "Mn",
      "n_tetrahedral": 123,
      "n_octahedral": 656,
      "L23_minus_L3_balanced_accuracy": -0.0033028455284553893
    },
    {
      "element": "Fe",
      "n_tetrahedral": 226,
      "n_octahedral": 865,
      "L23_minus_L3_balanced_accuracy": -0.0022123893805310324
    },
    {
      "element": "Co",
      "n_tetrahedral": 198,
      "n_octahedral": 530,
      "L23_minus_L3_balanced_accuracy": 0.010739470173432464
    },
    {
      "element": "Ni",
      "n_tetrahedral": 101,
      "n_octahedral": 387,
      "L23_minus_L3_balanced_accuracy": -0.0012919896640827266
    },
    {
      "element": "Cu",
      "n_tetrahedral": 336,
      "n_octahedral": 109,
      "L23_minus_L3_balanced_accuracy": 0.006075251201397958
    }
  ]
}
```
