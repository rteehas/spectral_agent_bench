#!/usr/bin/env python3
"""Mandatory comparison to the actual published Figure 5 colored line support.

This does not import candidate code and never treats source integrity as a paper
pass. It renders submitted source-linked site arrays with one fixed paper-derived
style, uses the frozen independently authored contract, and requires every one
of sixteen element/color comparisons. Scientific acceptance remains separate.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')
PALETTE = {'octahedral': '#e41a1c', 'tetrahedral': '#377eb8'}
# Frozen without candidate-score optimization. The faint isolated reference
# strokes have RGB ~254,251/252,251/252 (red), 251/252,252/253,254 (blue).
# Version 2 retains opacity .015 and corrects width to 1.65 source pixels
# using independent isolated-source-stroke calibration. V1 failure is retained.
# Unknown historical renderer details remain a reason for failure, not relaxation.
RENDERER = {'opacity': .015, 'line_width_source_pixels': 1.65,
            'dpi': 100, 'canvas_pixels': [1972, 978],
            'palette': PALETTE, 'order': 'first contributing native source-record order',
            'fitted_to_candidate': False}
CALIBRATION = {
    'Ti': {'xpix': [149,249,349,449.5], 'xval': [455,465,475,485], 'box': [93,130,542,468]},
    'V': {'xpix': [595.5,694.5,792.5,891.5,989.5], 'xval': [510,520,530,540,550], 'box': [568,130,1009,468]},
    'Cr': {'xpix': [1096,1196.5,1296.5,1396.5], 'xval': [575,585,595,605], 'box': [1042,130,1490,468]},
    'Mn': {'xpix': [1579.5,1678.5,1778.5,1877.5], 'xval': [640,650,660,670], 'box': [1524,130,1969,468]},
    'Fe': {'xpix': [119.5,219,318.5,418.5,518], 'xval': [705,715,725,735,745], 'box': [93,548,542,884]},
    'Co': {'xpix': [628.5,728,827.5,926.5], 'xval': [780,790,800,810], 'box': [568,548,1013,884]},
    'Ni': {'xpix': [1108,1208.5,1308.5,1408.5], 'xval': [855,865,875,885], 'box': [1042,548,1490,884]},
    'Cu': {'xpix': [1541.5,1641.5,1741.5,1841.5,1941.5], 'xval': [930,940,950,960,970], 'box': [1524,548,1969,884]},
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_curves(output, inputs):
    rows = list(csv.DictReader((output/'sites.csv').open()))
    seen_keys = set()
    curves, audit = {}, {}
    for el in ELEMENTS:
        records = {}
        with gzip.open(inputs/f'{el}.jsonl.gz', 'rt') as stream:
            for i, line in enumerate(stream):
                r = json.loads(line)
                if r['name'] in records:
                    raise ValueError('Native duplicate source name')
                records[r['name']] = (i, r)
        selected = []
        seen_source_pairs = set()
        with np.load(output/f'{el}.npz', allow_pickle=False) as archive:
            for row in rows:
                if row.get('element') != el:
                    continue
                env = row.get('environment')
                if env not in PALETTE:
                    continue
                # Optional displayed flag may exclude other motifs, never omit
                # an explicitly submitted octahedral/tetrahedral observation.
                if row.get('displayed', '1') not in ('1', 'true', 'True'):
                    raise ValueError(f'Hidden displayed-class observation: {el}/{row.get("key")}')
                key = row['key']
                if (el, key) in seen_keys:
                    raise ValueError(f'Duplicate site key: {el}/{key}')
                seen_keys.add((el, key))
                source_ids = [row['source_l2'], row['source_l3']]
                if any(s not in records for s in source_ids):
                    raise ValueError(f'Unknown or missing native paired source: {el}/{key}')
                source_pair=tuple(source_ids)
                if source_pair in seen_source_pairs:
                    raise ValueError(f'Duplicate native site pair plotted twice: {el}/{key}')
                seen_source_pairs.add(source_pair)
                r2, r3 = [records[s][1] for s in source_ids]
                if (r2['edge'], r3['edge']) != ('L2', 'L3'):
                    raise ValueError(f'Incorrect native edge mapping: {el}/{key}')
                if r2['absorbing_atom'] != r3['absorbing_atom'] or r2['mp-id'] != r3['mp-id']:
                    raise ValueError(f'Unpaired native site: {el}/{key}')
                def physical(record):
                    sd=record['structure']
                    return (sd['lattice']['matrix'],[(s['abc'],s['species']) for s in sd['sites']])
                if physical(r2) != physical(r3):
                    raise ValueError(f'Cross-structure native edge pairing: {el}/{key}')
                for raw in (r2,r3):
                    species=raw['structure']['sites'][raw['absorbing_atom']]['species']
                    if len(species)!=1 or species[0]['element']!=el or species[0]['occu']!=1:
                        raise ValueError(f'Incorrect native absorbing species: {el}/{key}')
                a = np.asarray(archive[key], dtype=float)
                if (a.ndim != 2 or a.shape[1] != 2 or len(a) < 20 or
                    not np.isfinite(a).all() or not np.all(np.diff(a[:,0]) > 0)):
                    raise ValueError(f'Invalid energy/intensity array: {el}/{key}')
                y = a[:,1]
                if y.max() <= 0 or np.ptp(y) <= abs(y.max())*1e-8:
                    raise ValueError(f'Constant or nonpositive response: {el}/{key}')
                # Caption permits exactly one normalization of the whole curve.
                x, y = a[:,0], y/y.max()
                native_x = np.asarray(r3['spectrum'][0])
                if x[0] > native_x[0]+1e-6 or x[-1] < native_x[-1]-1e-6:
                    raise ValueError(f'Submitted site truncates native L3 support: {el}/{key}')
                selected.append({'key': key, 'environment': env, 'x': x, 'y': y,
                    'order': min(records[s][0] for s in source_ids)})
        if {r['environment'] for r in selected} != set(PALETTE):
            raise ValueError(f'Missing published environment class: {el}')
        curves[el] = sorted(selected, key=lambda r:r['order'])
        audit[el] = {'curves': len(selected), 'by_environment': {
            env: sum(r['environment']==env for r in selected) for env in PALETTE}}
    return curves, audit


def render(curves, path):
    width, height = RENDERER['canvas_pixels']
    dpi = RENDERER['dpi']
    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    for el in ELEMENTS:
        c = CALIBRATION[el]
        x0,y0,x1,y1 = c['box']
        m,b = np.polyfit(c['xpix'], c['xval'], 1)
        py0,py1 = (465.5,145.5) if el in ELEMENTS[:4] else (883.5,563.5)
        ax = fig.add_axes([x0/width,(height-y1)/height,(x1-x0)/width,(y1-y0)/height])
        ax.set_xlim(m*x0+b,m*x1+b)
        ax.set_ylim((py0-y1)/(py0-py1),(py0-y0)/(py0-py1))
        ax.axis('off')
        for curve in curves[el]:
            ax.plot(curve['x'],curve['y'],color=PALETTE[curve['environment']],
                alpha=RENDERER['opacity'],
                lw=RENDERER['line_width_source_pixels']*72/dpi,
                solid_capstyle='projecting',solid_joinstyle='round')
    fig.savefig(path,dpi=dpi)
    plt.close(fig)
    return np.asarray(Image.open(path).convert('RGB'))


def masks(rgb):
    r,g,b = rgb.astype(np.int16).transpose(2,0,1)
    return {'octahedral': ((r-g)>=3)&((r-b)>=3),
            'tetrahedral': ((b-r)>=3)&((b-g)>=3)}


def compare(reference, candidate, contract):
    result = {}
    tolerance = float(contract['spatial_tolerance_source_pixels'])
    for el in ELEMENTS:
        x0,y0,x1,y1 = CALIBRATION[el]['box']
        # Complete calibrated interior, with no residual-dependent peak/tail mask.
        target_masks = masks(reference[y0:y1,x0:x1])
        candidate_masks = masks(candidate[y0:y1,x0:x1])
        part = {}
        for env in PALETTE:
            target, actual = target_masks[env], candidate_masks[env]
            errors=[]
            item={'paper_pixels':int(target.sum()),'submitted_pixels':int(actual.sum()),'errors':errors}
            if not target.any() or not actual.any():
                errors.append('Empty published/submitted class mask')
            else:
                actual_distances=distance_transform_edt(~target)[actual]
                target_distances=distance_transform_edt(~actual)[target]
                precision=float(np.mean(actual_distances <= tolerance))
                recall=float(np.mean(target_distances <= tolerance))
                directed90=[float(np.percentile(actual_distances,90)),float(np.percentile(target_distances,90))]
                item.update({'precision_within_tolerance':precision,
                    'recall_within_tolerance':recall,'directed_distance_90th_percentile_pixels':directed90})
                if precision < contract['per_panel_per_color_precision_minimum']:
                    errors.append('Predicted visible support precision below frozen minimum')
                if recall < contract['per_panel_per_color_recall_minimum']:
                    errors.append('Published visible support recall below frozen minimum')
                if max(directed90) > contract['per_panel_per_color_90th_percentile_directed_distance_maximum_pixels']:
                    errors.append('Directed 90th-percentile distance exceeds frozen tolerance')
            item['pass']=not errors
            part[env]=item
        result[el]=part
    return result


def verify(output, inputs, truth, render_path):
    contract_path=truth/'figure5_comparison_contract.json'
    contract=json.loads(contract_path.read_text())
    figure_path=truth/'figure5.png'
    reference=np.asarray(Image.open(figure_path).convert('RGB'))
    if list(reference.shape[:2][::-1]) != RENDERER['canvas_pixels']:
        raise ValueError('Published figure dimensions differ from frozen calibration')
    curves,audit=load_curves(output,inputs)
    render_path.parent.mkdir(parents=True,exist_ok=True)
    candidate=render(curves,render_path)
    panels=compare(reference,candidate,contract)
    return {'paper_doi':'10.1038/s41597-021-00936-5',
        'target':'Original Figure 5, all eight panels and both coordination colors',
        'figure_sha256':sha256(figure_path),'contract_sha256':sha256(contract_path),
        'renderer':RENDERER,'source_identity_audit':audit,'panels':panels,
        'paper_plot_pass':all(v['pass'] for p in panels.values() for v in p.values()),
        'scientific_pass':None,'independent_source_replay_required':True,
        'mandatory_manual_review':'All eight full panels, unusual curves, and late-metal L2/post-edge class contrasts; no opacity-derived population inference.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--truth',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    try:
        result=verify(args.output,args.inputs,args.truth,args.out.with_suffix('.rendered.png'))
    except (KeyError,ValueError,OSError,TypeError) as exc:
        result={'paper_plot_pass':False,'scientific_pass':None,'errors':[str(exc)]}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['paper_plot_pass'] else 1)


if __name__=='__main__':
    main()
