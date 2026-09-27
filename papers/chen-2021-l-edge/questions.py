"""Minimal solver-facing questions; no worked protocol or expected findings."""
BACKGROUND = (
    'These are site-resolved FEFF L2 and L3 XANES calculations for Ti, V, Cr, Mn, Fe, Co, Ni and Cu. '
    'Each gzip file contains one native JSON record per line. "spectrum" holds [photon energies in eV, absorption intensities]; '
    '"absorbing_atom" is a zero-based index into "structure.sites". "mp-id" is the released material identifier; "name" identifies a calculation. '
    'Structures include lattice vectors and fractional coordinates. Intensities retain the released relative scale.'
)
DELIVER = 'Return a report with quantitative evidence, methodological justification and limitations, supporting figures, and runnable code. '
QUESTIONS = [
    {
        'id': 'Q1',
        'title': 'When do simplified treatments of inequivalent sites distort a material’s L-edge fingerprint?',
        'instruction': (
            'Determine how strongly material-level L2 and L3 fingerprints depend on differences among absorbing sites and their populations, '
            'and whether finite energy resolution changes which materials are most affected. Establish where the available calculations support a complete material response. '
            + DELIVER +
            'Include responses.npz (material__element__edge keys, energy and intensity columns), sites.csv identifying contributing raw records and their populations, '
            'and numerical evidence for the comparisons.'
        ),
        'derivation': 'The site-to-material aggregation stage of the high-throughput workflow. The sensitivity of resulting fingerprints to simplified site treatment is a new release-based investigation.',
    },
    {
        'id': 'Q2',
        'title': 'Does local coordination geometry predict the balance of L3 and L2 spectral weight across transition-metal compounds?',
        'instruction': (
            'Determine whether tetrahedral and octahedral environments differ in their L3-to-L2 spectral weight once chemical composition is taken into account. '
            'How robust is the relationship to the definitions of local geometry and spectral weight, and what physical interpretation do these calculations support? '
            + DELIVER +
            'Include sites.csv identifying each raw observation and the structural and spectral quantities used; define their meaning and units in the report.'
        ),
        'derivation': 'The comparison of local environments and L-edge intensity balance motivates this conditional analysis. The release contains structures and separate edge spectra, but no historical labels or exact figure arrays.',
    },
    {
        'id': 'Q3',
        'title': 'Does the L2 edge add transferable coordination information beyond the L3 edge?',
        'instruction': (
            'Determine whether including L2 improves identification of tetrahedral and octahedral absorbing environments from spectra when the test compositions are absent from model development. '
            'Assess how the conclusion depends on chemistry and energy resolution. Structures may define the reference environments but must not enter spectral prediction. '
            + DELIVER +
            'Include sites.csv with source identities and reference environments, predictions.csv (name,method,split,predicted), '
            'and partitions.csv (material,method,split,role).'
        ),
        'derivation': 'The stated use of L-edge spectra for local-environment inference. The paired-edge transfer comparison is a new benchmark experiment; the release contains no original machine-learning predictions or splits.',
    },
]
