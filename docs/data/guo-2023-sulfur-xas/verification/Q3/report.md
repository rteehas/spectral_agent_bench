# Spectral inference of phosphorus coordination

Crystal-only training transfers some coordination information to the glass spectra but fails to recover most bridging sulfur sites. At FWHM0.5eV, its balanced accuracy is 0.679, compared with 0.871 for grouped glass training and 0.896 for hybrid training. Crystal-only P2 recall is 31.1%, whereas grouped-glass recall is 71.1%. The majority control reaches 97.0% ordinary accuracy while its balanced accuracy is only 0.333; ordinary accuracy would therefore give a misleading impression of useful coordination inference.

At1eV the balanced accuracies are 0.728, 0.893 and 0.926 for crystal, grouped-glass and hybrid training respectively. Crystal-only P2 recall remains 33.3%, versus 77.8% for grouped-glass training. Thus the tested Gaussian broadening preserves the training-regime ordering and does not degrade these point estimates; smoothing may regularize this fixed model. This comparison does not establish a statistically significant broadening benefit because no paired interval for score differences or refitting uncertainty was estimated. Adding glass training is associated with better minority transfer within the archive, but the unequal training-library sizes and coverage prevent attributing that gain solely to structural disorder.

The target is the periodic number of P atoms within2.6Å of the absorber. It is a geometry-derived operational label, not a supplied experimental annotation. Only normalized spectral intensities on a common excitation-energy grid enter the classifier. Structure, composition, multiplicity, filenames and site IDs are never predictors. Crystal sites supply one training regime; glass-only and hybrid training exclude every site of the tested material. Four deterministic shuffled glass-material folds evaluate all48 glasses. Same-composition and related ancestral structures can cross folds; this tests new structures from the archive, not new chemistries or synthesis routes.

Each condition uses a fixed random forest160 trees, minimum leaf2 and balanced bootstrap class weights; no target-dependent tuning is performed. We compare Gaussian FWHM0.5 and1eV, preserving sites and partitions. A crystal-training majority-class baseline demonstrates why aggregate accuracy is insufficient. Probability calibration and hyperparameter optimality are not claimed. Class-wise recall and confusion matrices expose rare-class failures. Conditional95% intervals resample48 material blocks500 times without refitting; training-set/model-selection uncertainty is not included.

Results:
{
  "crystal_RF_fwhm0.5": {
    "accuracy": 0.8448818897637795,
    "balanced_accuracy": 0.6787936003661811,
    "recall": [
      0.8709677419354839,
      0.854301948051948,
      0.3111111111111111
    ],
    "confusion": [
      [
        27,
        4,
        0
      ],
      [
        357,
        2105,
        2
      ],
      [
        0,
        31,
        14
      ]
    ],
    "balanced_accuracy_ci95": [
      0.5702181808667497,
      0.7589456379631474
    ]
  },
  "glass_group_RF_fwhm0.5": {
    "accuracy": 0.9929133858267717,
    "balanced_accuracy": 0.8711750764170119,
    "recall": [
      0.9032258064516129,
      0.9991883116883117,
      0.7111111111111111
    ],
    "confusion": [
      [
        28,
        3,
        0
      ],
      [
        0,
        2462,
        2
      ],
      [
        0,
        13,
        32
      ]
    ],
    "balanced_accuracy_ci95": [
      0.7781180553055257,
      0.9412720370370371
    ]
  },
  "hybrid_RF_fwhm0.5": {
    "accuracy": 0.9937007874015747,
    "balanced_accuracy": 0.8960257335257337,
    "recall": [
      1.0,
      0.9991883116883117,
      0.6888888888888889
    ],
    "confusion": [
      [
        31,
        0,
        0
      ],
      [
        0,
        2462,
        2
      ],
      [
        0,
        14,
        31
      ]
    ],
    "balanced_accuracy_ci95": [
      0.8249039451200624,
      0.9537037037037037
    ]
  },
  "crystal_RF_fwhm1": {
    "accuracy": 0.9366141732283465,
    "balanced_accuracy": 0.7282036959456315,
    "recall": [
      0.9032258064516129,
      0.948051948051948,
      0.3333333333333333
    ],
    "confusion": [
      [
        28,
        3,
        0
      ],
      [
        127,
        2336,
        1
      ],
      [
        0,
        30,
        15
      ]
    ],
    "balanced_accuracy_ci95": [
      0.6217703448654034,
      0.795160865396365
    ]
  },
  "glass_group_RF_fwhm1": {
    "accuracy": 0.9937007874015747,
    "balanced_accuracy": 0.8932620172539528,
    "recall": [
      0.9032258064516129,
      0.9987824675324676,
      0.7777777777777778
    ],
    "confusion": [
      [
        28,
        3,
        0
      ],
      [
        0,
        2461,
        3
      ],
      [
        0,
        10,
        35
      ]
    ],
    "balanced_accuracy_ci95": [
      0.8027739521692222,
      0.9687976075812261
    ]
  },
  "hybrid_RF_fwhm1": {
    "accuracy": 0.9948818897637796,
    "balanced_accuracy": 0.9255200817700818,
    "recall": [
      1.0,
      0.9987824675324676,
      0.7777777777777778
    ],
    "confusion": [
      [
        31,
        0,
        0
      ],
      [
        0,
        2461,
        3
      ],
      [
        0,
        10,
        35
      ]
    ],
    "balanced_accuracy_ci95": [
      0.850786204174653,
      0.9814814814814815
    ]
  },
  "crystal_majority": {
    "accuracy": 0.9700787401574803,
    "balanced_accuracy": 0.3333333333333333,
    "recall": [
      0.0,
      1.0,
      0.0
    ],
    "confusion": [
      [
        0,
        31,
        0
      ],
      [
        0,
        2464,
        0
      ],
      [
        0,
        45,
        0
      ]
    ],
    "balanced_accuracy_ci95": [
      0.3333333333333333,
      0.3333333333333333
    ]
  }
}

The most important comparison is minority coordination recall and balanced accuracy against the majority baseline, followed by crystal-only versus grouped glass/hybrid results. A high raw accuracy cannot establish successful transfer when most sites have one phosphorus neighbor. Crystal and glass libraries differ in size, class balance and environment coverage; their score difference cannot be attributed to disorder alone. Broader-resolution differences apply only to the controlled Gaussian experiment. The data are computed site spectra: this is neither a classifier for measured bulk spectra nor evidence of experimental detectability.

The report, definitions, per-site table, predictions and material partitions allow independent reconstruction. The training regimes and uncertainty must be scientifically reviewed as well as arithmetically checked. Minority labels are concentrated in a small number of structures, limiting generalization even when point estimates improve.
