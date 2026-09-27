#!/usr/bin/env python3
"""Check a reconstruction against the actual published Figure 4 vector paths.

No candidate-analysis imports, model-derived answer key or fitted bandwidth.
Both retained material panels are mandatory. One L3-peak registration is the
only energy adjustment performed by this evaluator.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path

import numpy as np

REQUIRED = {
    "MgMn2O4": {"material_id": "mp-32006", "element": "Mn", "primary_window_eV": [638, 646],
                "secondary_window_eV": [649, 657],
                "source_record_ids": ["mp-32006-2-XANES-L2", "mp-32006-2-XANES-L3"]},
    "LiFePO4": {"material_id": "mp-761468", "element": "Fe", "primary_window_eV": [702, 711],
                "secondary_window_eV": [716, 724],
                "source_record_ids": ["mp-761468-4-XANES-L2", "mp-761468-4-XANES-L3"]},
}


def peak(x, y, window):
    keep = (x >= window[0]) & (x <= window[1])
    if np.count_nonzero(keep) < 3:
        raise ValueError("Insufficient points in peak window")
    ids = np.flatnonzero(keep)
    i = ids[np.argmax(y[ids])]
    if i == ids[0] or i == ids[-1]:
        raise ValueError("Peak lies at the search-window boundary")
    return float(x[i]), float(y[i])


def reference(material, rows, calibration):
    records = [r for r in rows if r["material"] == material and r["curve"] == "feff"]
    x = np.asarray([float(r["energy_eV"]) for r in records])
    y = np.asarray([float(r["display_intensity"]) for r in records])
    lo, hi = calibration[material]["visible_energy_range_eV"]
    lo, hi = max(lo, x[0]), min(hi, x[-1])
    # Retain line segments that cross the clipping rectangle. Filtering only
    # visible vertices would silently discard the last displayed segment.
    xx = np.r_[lo, x[(x > lo) & (x < hi)], hi]
    return xx, np.interp(xx, x, y)


def verify(submission, provenance, truth, check_protocol_claims=True):
    rows = list(csv.DictReader((truth/"figure4_traces.csv").open()))
    calibration = json.loads((truth/"figure4_calibration.json").read_text())
    contract = json.loads((truth/"figure4_comparison_contract.json").read_text())
    candidate_rows = list(csv.DictReader(submission.open()))
    metadata = json.loads(provenance.read_text())
    # Support a plain per-material mapping only; do not infer unknown IDs.
    if not isinstance(metadata, dict):
        raise ValueError("Provenance must be a per-material mapping")
    report = {"paper_doi": "10.1038/s41597-021-00936-5",
              "verification_target": "Original published Figure 4 green vector paths",
              "required_materials": list(REQUIRED), "panels": {},
              "protocol_metadata_checked": check_protocol_claims,
              "scientific_review_required": True}
    for material, expected in REQUIRED.items():
        errors = []
        result = {"pass": False, "errors": errors}
        report["panels"][material] = result
        try:
            r = [r for r in candidate_rows if r["material"] == material]
            if len(r) < 20:
                raise ValueError("Missing or insufficient curve")
            x = np.asarray([float(t["energy_eV"]) for t in r])
            y = np.asarray([float(t["intensity"]) for t in r])
            if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.all(np.diff(x) > 0):
                raise ValueError("Nonfinite values or nonmonotone energies")
            if y.max() <= 0 or np.ptp(y) <= abs(y.max())*1e-8:
                raise ValueError("Spectrum must be nonconstant and have a positive maximum")
            # Physical native units are permitted. This is the paper's single
            # global maximum normalization, never a baseline subtraction.
            y = y/y.max()
            m = metadata[material]
            if m["material_id"] != expected["material_id"] or m["element"] != expected["element"]:
                errors.append("Wrong released material or absorbing element")
            if not m.get("source_record_ids") or not isinstance(m["source_record_ids"], list):
                errors.append("Missing native source-record identifiers")
            elif sorted(m["source_record_ids"]) != expected["source_record_ids"]:
                errors.append("Native source identifiers do not match the released material/edge pair")
            if check_protocol_claims:
                if float(m["broadening_fwhm_eV"]) != 1.2:
                    errors.append("Broadening differs from the published 1.2 eV FWHM")
                if float(m.get("energy_shift_eV", 0)) != 0:
                    errors.append("Submit native energies; the evaluator performs the one permitted registration")
            tx, ty = reference(material, rows, calibration)
            target_peak, _ = peak(tx, ty, expected["primary_window_eV"])
            # The native FEFF absolute energy is close to the displayed edge;
            # permit a broad initial location window without optimizing shape.
            native_window = [expected["primary_window_eV"][0]-10,
                             expected["primary_window_eV"][1]+5]
            candidate_peak, _ = peak(x, y, native_window)
            shift = target_peak-candidate_peak
            sx = x+shift
            width_eV = calibration[material]["feff_stroke_width_eV"]
            left_gap, right_gap = max(0., sx[0]-tx[0]), max(0., tx[-1]-sx[-1])
            coverage = max(0., min(sx[-1], tx[-1])-max(sx[0], tx[0]))/(tx[-1]-tx[0])
            result.update({"registered_energy_shift_eV": shift,
                           "visible_reference_range_eV": [float(tx[0]), float(tx[-1])],
                           "coverage_fraction": float(coverage),
                           "uncovered_left_eV": float(left_gap), "uncovered_right_eV": float(right_gap)})
            if coverage < contract["minimum_visible_reference_coverage_fraction"]:
                errors.append("Insufficient published-curve coverage")
            if max(left_gap, right_gap) > width_eV:
                errors.append("An uncovered endpoint exceeds one published stroke width")
            grid = np.arange(tx[0], tx[-1]+1e-9, contract["comparison_grid_spacing_eV"])
            # Do not choose the overlap after seeing errors. Any sub-stroke
            # unobserved endpoint uses nearest endpoint extension; it is included
            # in every error metric and also reported by the coverage gates.
            residual = np.interp(grid, sx, y)-np.interp(grid, tx, ty)
            rmse = float(np.sqrt(np.mean(residual**2)))
            maximum = float(np.max(np.abs(residual)))
            result.update({"comparison_points": len(grid), "normalized_rmse": rmse,
                           "normalized_maximum_absolute_residual": maximum})
            if rmse > contract["normalized_rmse_maximum"]:
                errors.append("Full-curve normalized RMSE exceeds the fixed paper tolerance")
            if maximum > contract["normalized_absolute_residual_maximum"]:
                errors.append("Maximum local residual exceeds the fixed paper tolerance")
            sp, sh = peak(tx, ty, expected["secondary_window_eV"])
            cp, ch = peak(sx, y, expected["secondary_window_eV"])
            result["secondary_peak"] = {"paper_energy_eV": sp, "candidate_energy_eV": cp,
                "energy_error_eV": abs(cp-sp), "paper_height": sh,
                "candidate_height": ch, "height_error": abs(ch-sh),
                "position_tolerance_eV": max(0.1, width_eV)}
            if abs(cp-sp) > max(0.1, width_eV):
                errors.append("Secondary-peak position disagrees with the published curve")
            if abs(ch-sh) > contract["peak_height_absolute_tolerance"]:
                errors.append("Secondary-peak height disagrees with the published curve")
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(str(exc))
        result["pass"] = not errors
    report["paper_numerical_pass"] = all(x["pass"] for x in report["panels"].values())
    report["scientific_pass"] = None
    return report


def verify_output(output, truth):
    """Read the task's responses.npz and sources.csv without extra solver files.

    Metadata declarations cannot establish that code used a particular
    bandwidth or avoided baseline transformations. Those facts are checked by
    the mandatory independent code execution/scientific review layer.
    """
    with np.load(output/"responses.npz", allow_pickle=False) as archive:
        response = {k:archive[k] for k in archive.files}
    source_rows=list(csv.DictReader((output/"sources.csv").open()))
    metadata,rows={},[]
    def field(row,*names):
        for name in names:
            if name in row:return row[name]
        raise ValueError(f"Missing source column among {names}")
    for material,expected in REQUIRED.items():
        key=f"{material}__{expected['element']}__L23"
        if key not in response:
            raise ValueError(f"Missing required response {key}")
        xy=np.asarray(response[key],dtype=float)
        if xy.ndim!=2 or xy.shape[1]!=2:
            raise ValueError(f"{key} must contain energy/intensity columns")
        for x,y in xy:
            rows.append({"material":material,"energy_eV":x,"intensity":y})
        records=[r for r in source_rows if field(r,"material","compound")==material]
        ids={field(r,"material_id","mp-id") for r in records}
        elements={field(r,"element","absorbing_element") for r in records}
        if len(ids)!=1 or len(elements)!=1:
            raise ValueError(f"Ambiguous or missing source identity for {material}")
        metadata[material]={"material_id":ids.pop(),"element":elements.pop(),
            "source_record_ids":[field(r,"name","source_record_id") for r in records]}
    with tempfile.TemporaryDirectory() as directory:
        d=Path(directory)
        with (d/"response.csv").open("w") as f:
            w=csv.DictWriter(f,["material","energy_eV","intensity"])
            w.writeheader();w.writerows(rows)
        (d/"sources.json").write_text(json.dumps(metadata))
        result=verify(d/"response.csv",d/"sources.json",truth,check_protocol_claims=False)
    result["input_contract"]="responses.npz and sources.csv"
    result["protocol_review"]="The mandatory independent replay must establish 1.2 eV FWHM processing, native energies, absence of baseline transforms, source selection and actual code-to-array provenance. A metadata claim is insufficient."
    return result


def plot_overlay(output, truth, report, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows=list(csv.DictReader((truth/"figure4_traces.csv").open()))
    calibration=json.loads((truth/"figure4_calibration.json").read_text())
    with np.load(output/"responses.npz",allow_pickle=False) as archive:
        response={k:archive[k] for k in archive.files}
    figure,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,(material,expected) in zip(axes,REQUIRED.items()):
        tx,ty=reference(material,rows,calibration)
        z=response[f"{material}__{expected['element']}__L23"]
        result=report["panels"][material]
        ax.plot(tx,ty,color="#4daf4a",lw=2,label="Published Figure 4 vector")
        ax.plot(z[:,0]+result["registered_energy_shift_eV"],z[:,1]/z[:,1].max(),
                color="#202020",lw=1,ls="--",label="Native-release reconstruction")
        ax.set(xlim=calibration[material]["visible_energy_range_eV"],ylim=(-.02,1.08),
               xlabel="Energy after one L3 registration (eV)",ylabel="Maximum-normalized intensity",
               title=f"{material}: RMS error {result['normalized_rmse']:.4f}")
        ax.legend(fontsize=8)
    figure.savefig(destination,dpi=170)
    plt.close(figure)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, help="Task output directory containing responses.npz and sources.csv")
    p.add_argument("--submission", type=Path)
    p.add_argument("--provenance", type=Path)
    p.add_argument("--truth", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--plot", type=Path, help="Optional published/reconstructed overlay PNG; requires --output")
    args=p.parse_args()
    if args.output:
        if args.submission or args.provenance:
            p.error("Use --output or --submission/--provenance, not both")
        result=verify_output(args.output,args.truth)
    else:
        if not args.submission or not args.provenance:
            p.error("Provide --output, or both --submission and --provenance")
        result=verify(args.submission, args.provenance, args.truth)
    text=json.dumps(result, indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    if args.plot:
        if not args.output:
            p.error("--plot requires --output")
        args.plot.parent.mkdir(parents=True,exist_ok=True)
        plot_overlay(args.output,args.truth,result,args.plot)
    print(text)
    raise SystemExit(0 if result["paper_numerical_pass"] else 1)


if __name__ == "__main__":
    main()
