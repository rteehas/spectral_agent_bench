#!/usr/bin/env python3
"""Recreate fictional, deterministic demo inputs and verification files. No measured data."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'docs/data/demo'
INPUTS = ROOT / 'inputs'
TRUTH = ROOT / 'verification'
INPUTS.mkdir(parents=True, exist_ok=True)
TRUTH.mkdir(parents=True, exist_ok=True)
x = [i / 239 for i in range(240)]

def curve(t, shift=0):
    return .13 + .57 / (1 + math.exp(-30 * (t - .4 - shift))) + .2 * math.exp(-((t - .52 - shift) / .06) ** 2)

def write(folder, name, **data):
    (folder / name).write_text(json.dumps({'synthetic': True, 'note': 'Fictional demonstration data; not measured spectra.', **data}, indent=2) + '\n')

a = [curve(t) for t in x]
b = [curve(t, .1) for t in x]
def mix(fraction):
    return [fraction * ai + (1 - fraction) * bi for ai, bi in zip(a, b)]

write(INPUTS, 'reference_spectra.json', axis=x, axis_unit='arbitrary units', references={'A': a, 'B': b})
write(INPUTS, 'reduction_spectrum.json', axis=x, axis_unit='arbitrary units', signal=mix(.7))
write(INPUTS, 'shifted_spectrum.json', axis=x, axis_unit='arbitrary units', signal=[curve(t, .03) for t in x])
write(INPUTS, 'cycle_spectra.json', axis=x, axis_unit='arbitrary units', spectra={'before_charge': mix(.8), 'after_charge': mix(.25), 'after_discharge': mix(.78)})
write(INPUTS, 'alternative_references.json', axis=x, axis_unit='arbitrary units', references={'A': a, 'B': b, 'C': mix(.5)})
write(INPUTS, 'ambiguous_spectrum.json', axis=x, axis_unit='arbitrary units', signal=mix(.5))
write(TRUTH, 'mixture_fit.json', coefficients={'A': .7, 'B': .3}, absolute_coefficient_tolerance=.001, note_for_review='Compare recovered nonnegative, sum-to-one coefficients; the synthetic mixture is noiseless.')
write(TRUTH, 'alignment_check.json', reference='A', axis_shift=.03, shift_unit='arbitrary units', absolute_shift_tolerance=.002, conclusion='An axis shift alone generates the discrepancy. A residual does not establish an additional species.')
write(TRUTH, 'cycle_fit.json', fraction_A={'before_charge': .8, 'after_charge': .25, 'after_discharge': .78}, charge_change=-.55, discharge_minus_initial=-.02, absolute_coefficient_tolerance=.001, conclusion='Recovery of a fit coefficient alone does not prove complete structural reversibility.')
write(TRUTH, 'nonunique_fit.json', equivalent_models=[{'A': .5, 'B': .5, 'C': 0}, {'A': 0, 'B': 0, 'C': 1}], conclusion='Reference C equals the mean of A and B, making the phase assignment non-unique. Independent evidence is needed.')
print('Generated 6 synthetic input files and 4 verification files.')
