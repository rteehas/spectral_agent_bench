# Independent release-method audit

Agent: execution_review. Date: 2026-09-26.

Public source: https://github.com/atomisticnet/xas-tools/releases/tag/v0.1.0
Checked-out commit: a7d08913fc59d6509459268279b33195cf20e30b.

## Exact independent reconstruction of all released material raw spectra

For each site, read final OSZICAR E0 (not F), its efermi.txt, and the three diagonal mu.dat intensity columns. The neutral E0 is scaled by the corehole/neutral POSCAR atom-count ratio if needed. The successful alignment is

E_aligned = E_mu + E0_corehole - (N_corehole/N_neutral) E0_neutral - E_fermi_corehole.

The material grid is linspace(minimum aligned lower endpoint, maximum aligned upper endpoint, maximum site row count). Interpolate each site's sum of three diagonal intensities to this grid using scipy.interpolate.interp1d(kind='cubic', bounds_error=False, fill_value=0), multiply by the integer after the underscore in its directory name, and sum sites. The released raw files contain summed intensity, without division by three or sum of multiplicities. Such scalar factors do not affect area-normalized fingerprints.

Independent comparison used all 66 material-*_raw.txt files as held-back targets. Maximum relative L2 residual: 3.091052146507603e-12 (material 52). Every material grid has exactly the maximum number of rows of its constituent mu.dat files; aligned endpoint errors never exceed floating-point roundoff. The separate portable implementation is `reconstruct_release.py`, with full numerical results in `reconstruction_results.json`. Run it with `--raw-root PATH/22-05-13-LPS-no-POTCAR --reference-root PATH/Spectra_66_compounds --output reconstruction_results.json` after extracting the two original public archives. This historical source audit is evaluator-side only; candidate workflows do not need either extracted archive. It does not import the candidate pipeline.

## Release-code pitfalls

1. xas_tools/vasp.py parse_vasp_chp_output shifts by total-energy differences but does not subtract the stored corehole Fermi energy. That function therefore does not reproduce the released raw material spectra. It also assumes full OUTCAR and CONTCAR files, which were removed by compression; the supplied compressed release must be read directly.
2. Its dielectric parser sums all columns after energy, including off-diagonal components, whereas mu.dat keeps only the three diagonal components.
3. AbsorptionSpectrum.spectrum aliases the first site's stored intensity and mutates it via += on every access. Repeated accesses or plots silently overcount.
4. The example notebook misspells calculate_broadened as calculated_broadened. It uses Gaussian FWHM .3 and Lorentz widths .1 to .5, different from the manuscript's .5 and .59+.1*(E-Ecbm).
5. util.broaden applies a linearly varying Lorentz width at each output energy rather than at each source energy, clips requested xlim to input-domain overlap, preserves the original endpoint intensity, omits the final nonzero source bin, and uses central-spacing quadrature. These quirks matter for exact legacy reproduction.
6. Multiplicities are symmetry counts divided by their gcd, not the absolute number of sulfur atoms in a supercell. The absorbing S is the first atom of each corehole POSCAR; directory indices enumerate inequivalent site types rather than neutral-cell global indices.

## Environment

/tmp/guo-bench-env/bin/python has numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, ase 3.29.0 and scikit-learn 1.9.1. This is sufficient for direct postprocessing, structure-derived labels, and candidate statistical analysis without VASP or licensed POTCAR files.

The _broaden_shift files have an absolute calibration and intensity normalization not documented in the release code, so the independently reproducible _raw references are the stronger numeric oracle. Exact agreement of an invented broadening procedure with _broaden_shift was not established.
