# Published evidence, independent of benchmark solutions

These are evaluator assets for Chen et al., *Database of ab initio L-edge X-ray absorption near edge structure*, Scientific Data **8**, 153 (2021), [doi:10.1038/s41597-021-00936-5](https://doi.org/10.1038/s41597-021-00936-5). The article and its figures are distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The retained PDF and publisher PNG figures are unmodified. The CSV files are derived from the published figures by the transformations described below.

## Figure 2: exact printed numbers

`figure2_counts.csv` transcribes all 69 numbered element cells in `figure2.png`. The upper number is the number of per-element crystal averages with complete L2 and L3 site coverage; the lower number is the number of individual site-edge spectra. These are exact integer targets, with zero numerical tolerance. Blank and grey cells are not silently converted to zero.

The release must independently reproduce the printed numbers for any question that claims to reproduce this inventory. A release-versus-publication discrepancy is a discrepancy, even if a candidate and an independent release reconstruction agree. It is not repaired by replacing the published counts with candidate-derived values.

## Figure 4: original vector curves

`figure4_traces.csv` contains all 2,666 original vertices from the eighteen experiment, OCEAN and FEFF curves in PDF page 5. These are vector paths from the published PDF, **not curves recomputed from the release**. Each record retains its original page coordinates, drawing index, physical energy, displayed ordinate and clipping status. `figure4_calibration.json` records the labelled ticks, affine transformations, visible ranges and stroke widths for each panel.

The energy calibration uses all labelled ticks. Its largest residual is below 0.00025 eV. Intensity calibration uses the labelled 0 to 2.5 ticks. Red and blue curves have visual offsets of 1.1 and 0.55 respectively; the literal displayed ordinates are retained alongside offset-subtracted values. The green FEFF curves have no visual offset. Paths outside the plotting rectangle are not visible evidence and must not enter the comparison.

`figure4_comparison_contract.json` freezes full-curve, coverage and identifiable-feature requirements from the source figure's precision. It was written before the figure-truth author inspected candidate spectra. The stroke widths, rather than observed candidate errors, set the scale of the tolerances. One rigid energy shift and maximum normalization reflect the article's display conventions; the article specifies Gaussian broadening of 1.2 eV FWHM. No independent L2 alignment, arbitrary baseline fit, or fitted smoothing is allowed.

Only panels with a traceable released counterpart can be counted as successful reproductions. Keeping all six published panels here does not claim that the native release contains all six corresponding structures.

## Figure 5: raster overplot

`figure5.png` is the full-size publisher image. The PDF contains a raster image of this figure, rather than recoverable individual vector traces. Its translucent red and blue overplots encode octahedral and tetrahedral environments. Darkness cannot be converted into empirical quantiles, class frequencies or a unique per-spectrum numerical answer key. Any comparison must inspect the reconstructed full overplot and the actual published features; agreement with a newly computed class mean is insufficient.

The original frozen image comparison passed only 10 of 16 mandatory panel/color tests. A later, independently audited calibration using only isolated strokes in the published image established that the original assumed one-pixel stroke width was inaccurate. Contract version 2 changes that rendering width to 1.65 pixels; all scientific thresholds, coordinates, opacity, colors and hue masks remain unchanged. The original contract and failed result are retained. Version 2 also passes only 10 of 16 tests, so this research candidate remains **unvalidated and withheld from scoring**. The result does not establish that its physics is wrong: the author plotting settings and labels are unavailable, and translucent color support depends on compositing. No further style fitting or threshold relaxation was used to obtain acceptance.

Source-only calibration records and independent regression results are in `../reviews/source_renderer_calibration.json`, `../reviews/source_renderer_calibration_holdout.json` and `../reviews/source_renderer_independent_audit.json`. The calibration and audit scripts in the paper's `paper_results` directory read only the published figure.

## Rebuild

From the repository root, with NumPy and PyMuPDF installed:

```bash
python papers/chen-2021-l-edge/paper_results/extract_paper_truth.py \
  --pdf docs/data/chen-2021-l-edge/paper_results/verification/figures/paper.pdf \
  --out docs/data/chen-2021-l-edge/paper_results/verification/figures
```

The extraction reads no native release data, candidate artifacts, or former benchmark answer key. `provenance.json` records the article identifier, PDF hash and extraction software. Publisher full-size figure URLs follow `https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41597-021-00936-5/MediaObjects/41597_2021_936_FigN_HTML.png` for figure number `N`.
