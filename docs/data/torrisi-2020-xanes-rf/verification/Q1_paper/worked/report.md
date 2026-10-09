# Pointwise coordination reproduction

Random forests use the supplied 100-point spectra, fixed partitions, training-only random oversampling, and ten prescribed seeds. Validation rows are never added to training. No test labels are available to this program.

| Element | Validation accuracy | Validation F1: CN4 | CN5 | CN6 |
|---|---:|---:|---:|---:|
| Ti | 0.8453 | 0.7511 | 0.8468 | 0.8599 |
| V | 0.8390 | 0.9206 | 0.7620 | 0.8414 |
| Cr | 0.8995 | 0.9648 | 0.8034 | 0.9203 |
| Mn | 0.8431 | 0.5062 | 0.8410 | 0.8639 |
| Fe | 0.8679 | 0.8852 | 0.8509 | 0.8794 |
| Co | 0.8277 | 0.8108 | 0.6836 | 0.9049 |
| Ni | 0.8452 | 0.6647 | 0.7527 | 0.9066 |
| Cu | 0.8372 | 0.7219 | 0.8772 | 0.7815 |

These are validation scores. The evaluator computes final test scores from the submitted predictions and withheld labels. The ten fits vary the forest seed, not the split; this experiment does not establish unseen-material or experimental generalization.

Run: `python code/reproduce_coordination.py --inputs INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY --jobs 4`.
