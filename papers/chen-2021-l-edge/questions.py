"""Minimal research questions. Paper targets and worked methods stay evaluator-only."""

BACKGROUND = (
    'These are site-resolved FEFF L2 and L3 XANES calculations for Ti, V, Cr, Mn, Fe, Co, Ni and Cu. '
    'Each gzip file contains one native JSON record per line. "spectrum" holds '
    '[photon energies in eV, absorption intensities]; "absorbing_atom" is a zero-based index '
    'into "structure.sites". "mp-id" is the released material identifier; "name" identifies '
    'a calculation. Structures contain lattice vectors and fractional coordinates. '
    'Intensities retain the released relative scale.'
)

QUESTIONS = [
    {
        'id': 'R1',
        'title': 'Which L2,3 spectral features distinguish spinel MgMn2O4 and olivine LiFePO4?',
        'instruction': (
            'Which L2,3 spectral features distinguish spinel MgMn2O4 and olivine LiFePO4 '
            'at 1.2 eV Gaussian FWHM resolution? Establish their material responses and '
            'quantify the differences in peak structure and relative intensities. '
            'Return a report, supporting figures, runnable code, responses.npz '
            '(compound__element__edge keys, energy and intensity columns), and sources.csv '
            '(material, material_id, element, name) identifying the contributing native calculations.'
        ),
        'derivation': (
            'Material-level spectral reconstruction and line-shape characterization, '
            'verified against the computed curves in Figure 4(c,d). The other four '
            'panels are excluded, with the failed comparisons and missing inputs documented.'
        ),
    },
    {
        'id': 'R2',
        'title': 'How do coordination and absorber identity shape Ti–Cu L2,3 spectra?',
        'instruction': (
            'How do Ti–Cu L2,3 line shapes differ between octahedral and tetrahedral '
            'coordination, and how does spectral structure evolve across this series? '
            'Establish the coordination-resolved spectral evidence from the released '
            'structures and calculations. Return a report, figures for every element, '
            'runnable code, one ELEMENT.npz file per element (site keys; energy and '
            'intensity columns), and sites.csv '
            '(element, key, source_l2, source_l3, environment) linking each response to '
            'its native calculations and coordination assignment.'
        ),
        'derivation': (
            'The structure-to-spectrum comparison in Figure 5. All eight published '
            'panels and their visible coordination-dependent line shapes are required '
            'comparison targets; source integrity alone is insufficient.'
        ),
    },
]
