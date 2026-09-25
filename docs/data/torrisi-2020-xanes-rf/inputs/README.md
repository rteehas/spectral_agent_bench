# Input schema

Each `<element>.jsonl.gz` is a gzip-compressed JSON Lines file. Each line describes one absorbing-site XANES spectrum for the named element. Rows retain their original order.

- `source_row`: zero-based row number in the source element file.
- `E`: photon-energy samples in eV.
- `mu`: absorption values at the corresponding energy samples.
- `coordination`: released absorbing-site coordination-number label.
- `avg_nn_dists`: mean nearest-neighbor distance in angstrom.
- `nn_min-max`: largest minus smallest nearest-neighbor distance in angstrom.
- `bader`: released Bader-charge label in electron-charge units, or null when unavailable.
- `metadata`: released spectrum origin and material identifier, where available.

These are the earliest spectral records supplied in the open release: they have already been interpolated onto energy grids and supplied with structural labels. They are not native FEFF output or detector-raw measurements.
