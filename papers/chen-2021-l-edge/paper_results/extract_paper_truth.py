#!/usr/bin/env python3
"""Extract evaluator truth from the published article, never from candidate output.

Requires PyMuPDF and NumPy. The PDF has vector Figure 4 traces; its Figure 2
labels and Figure 5 ensembles are raster images. Figure 2 values below are a
literal transcription of the published labels. All calibrations refer to
visible labelled axis ticks, not the reconstructed spectra.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pymupdf

PANELS = {
    # Axis labels read from Figure 4; indices are drawing objects on PDF page 5.
    "TiO2": {"panel": "a", "element": "Ti", "xticks": [389, 394, 399, 404, 409],
             "energies": [455, 460, 465, 470, 475], "yticks": [424, 429, 434, 439, 444, 449],
             "feff": 470, "spines": 471},
    "V2O5": {"panel": "b", "element": "V", "xticks": [277, 282, 287, 292, 297, 302, 307],
             "energies": [515, 520, 525, 530, 535, 540, 545], "yticks": [322, 327, 332, 337, 342, 347],
             "feff": 368, "spines": 369},
    "MgMn2O4": {"panel": "c", "element": "Mn", "xticks": [831, 836, 841, 846, 851, 856, 861, 866],
                "energies": [635, 640, 645, 650, 655, 660, 665, 670], "yticks": [881, 886, 891, 896, 901, 906],
                "feff": 927, "spines": 928},
    "LiFePO4": {"panel": "d", "element": "Fe", "xticks": [491, 496, 501, 506, 511, 516, 521],
                "energies": [705, 710, 715, 720, 725, 730, 735], "yticks": [535, 540, 545, 550, 555, 560],
                "feff": 581, "spines": 582},
    "Cu": {"panel": "e", "element": "Cu", "xticks": [602, 607, 612, 617, 622, 627, 632, 637],
           "energies": [930, 935, 940, 945, 950, 955, 960, 965], "yticks": [652, 657, 662, 667, 672, 677],
           "feff": 698, "spines": 699},
    "Pt": {"panel": "f", "element": "Pt", "xticks": [719, 726, 733, 740, 747],
           "energies": [11550, 11560, 11570, 11580, 11590], "yticks": [764, 769, 774, 779, 784, 789],
           "feff": 810, "spines": 811},
}

# element, upper label (site-averaged), lower label (site-wise).
# Empty/grey cells are not converted into a claim of zero calculations.
FIGURE2 = """Sc 366 1121
Ti 592 2117
V 849 3073
Cr 568 1848
Mn 996 3240
Fe 1245 4589
Co 1046 3786
Ni 982 3827
Cu 1502 4837
Zn 811 4422
Ga 491 1605
Ge 1569 6082
As 1144 4430
Se 1628 9890
Br 792 4833
Kr 7 28
Rb 980 3478
Sr 942 3207
Y 541 1698
Zr 468 1440
Nb 591 2185
Mo 767 3297
Tc 68 226
Ru 403 1174
Rh 382 1060
Pd 490 1560
Ag 612 2288
Cd 570 3087
In 486 1667
Sn 575 1626
Sb 1150 4344
Te 1078 5107
I 800 6976
Xe 54 201
Cs 1048 3464
Ba 1510 5154
Hf 232 718
Ta 401 1378
W 414 1306
Re 306 985
Os 257 819
Ir 334 940
Pt 434 1345
Au 291 842
Hg 403 1420
Tl 506 1617
Pb 594 2190
Bi 567 2491
La 725 2573
Ce 521 1839
Pr 438 1432
Nd 536 1674
Pm 4 14
Sm 380 1096
Eu 366 1036
Gd 345 990
Tb 360 1116
Dy 343 1004
Ho 359 1134
Er 372 1232
Tm 253 746
Yb 367 1130
Lu 261 827
Ac 5 10
Th 207 521
Pa 20 40
U 616 1732
Np 106 254
Pu 84 211"""


def points(drawing):
    out = []
    for item in drawing["items"]:
        if item[0] != "l":
            raise ValueError("Expected a literal line-segment polyline")
        if not out:
            out.append(tuple(item[1]))
        elif not np.allclose(out[-1], tuple(item[1]), atol=1e-6):
            raise ValueError("Discontinuous polyline")
        out.append(tuple(item[2]))
    return np.asarray(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(args.pdf)
    drawings = document[4].get_drawings()
    traces, calibration = [], {}
    for material, panel in PANELS.items():
        tick_x = [drawings[i]["rect"].x0 for i in panel["xticks"]]
        tick_y = [drawings[i]["rect"].y0 for i in panel["yticks"]]
        xcoef = np.polyfit(tick_x, panel["energies"], 1)
        ycoef = np.polyfit(tick_y, np.arange(6) * 0.5, 1)
        clip = drawings[panel["spines"]]["rect"]
        calibration[material] = {**panel,
            "x_tick_page_coordinates": tick_x,
            "y_tick_page_coordinates": tick_y,
            "x_affine_page_to_eV": xcoef.tolist(),
            "y_affine_page_to_display_intensity": ycoef.tolist(),
            "x_tick_max_calibration_residual_eV": float(np.max(np.abs(np.polyval(xcoef, tick_x)-panel["energies"]))),
            "y_tick_max_calibration_residual": float(np.max(np.abs(np.polyval(ycoef, tick_y)-np.arange(6)*0.5))),
            "visible_axis_page_bounds": list(clip),
            "visible_energy_range_eV": np.polyval(xcoef, [clip.x0, clip.x1]).tolist(),
            "feff_stroke_width_page_points": drawings[panel["feff"]]["width"],
            "feff_stroke_width_eV": float(abs(xcoef[0])*drawings[panel["feff"]]["width"]),
            "feff_stroke_width_intensity": float(abs(ycoef[0])*drawings[panel["feff"]]["width"]),
        }
        # Three immediately preceding colored curves: red, blue, green.
        for i, name, offset in [(panel["feff"]-2, "experiment", 1.1),
                                (panel["feff"]-1, "ocean", 0.55),
                                (panel["feff"], "feff", 0.0)]:
            drawing = drawings[i]
            rgb = drawing["color"]
            channel = {"experiment": 0, "ocean": 2, "feff": 1}[name]
            if rgb is None or rgb[channel] != max(rgb):
                raise ValueError(f"Unexpected source path color for {material}/{name}: {rgb}")
            xy = points(drawing)
            energy = np.polyval(xcoef, xy[:, 0])
            ordinate = np.polyval(ycoef, xy[:, 1])
            for j, (point, e, y) in enumerate(zip(xy, energy, ordinate)):
                traces.append({"panel": panel["panel"], "material": material,
                    "element": panel["element"], "curve": name,
                    "vertex": j, "energy_eV": float(e), "display_intensity": float(y),
                    "intensity_minus_visual_offset": float(y-offset),
                    "visual_offset": offset, "page_x": float(point[0]), "page_y": float(point[1]),
                    "pdf_drawing_index": i,
                    "visible": int(clip.x0 <= point[0] <= clip.x1 and clip.y0 <= point[1] <= clip.y1)})
    with (args.out/"figure4_traces.csv").open("w") as f:
        writer = csv.DictWriter(f, list(traces[0])); writer.writeheader(); writer.writerows(traces)
    (args.out/"figure4_calibration.json").write_text(json.dumps(calibration, indent=2)+"\n")
    with (args.out/"figure2_counts.csv").open("w") as f:
        writer=csv.writer(f);writer.writerow(["element", "paper_site_averaged", "paper_site_wise"])
        for line in FIGURE2.splitlines(): writer.writerow(line.split())
    provenance = {
        "article_doi": "10.1038/s41597-021-00936-5",
        "article_title": "Database of ab initio L-edge X-ray absorption near edge structure",
        "authors": "Chen et al.", "publication_year": 2021,
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source_pdf_url": "https://www.nature.com/articles/s41597-021-00936-5.pdf",
        "source_pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "publisher_images": {
            f"figure{n}.png": {
                "url": f"https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41597-021-00936-5/MediaObjects/41597_2021_936_Fig{n}_HTML.png",
                "sha256": hashlib.sha256((args.out/f"figure{n}.png").read_bytes()).hexdigest()
            } for n in [2,4,5] if (args.out/f"figure{n}.png").exists()
        },
        "extraction_software": f"PyMuPDF {pymupdf.VersionBind}",
        "figure4": {"pdf_page_one_based": 5, "method": "Original vector line vertices and axis tick positions; affine calibration from labelled ticks.",
                    "transformations": "Axis-coordinate calibration; retain literal display intensity and separately subtract visual offsets 0,0.55,1.1. No reconstruction from release data.",
                    "visible_only_note": "PDF paths extend beyond axis clips; only the visible portion is valid published comparison evidence.",
                    "n_vertices": len(traces), "n_curves": 18,
                    "uncertainty": "Original vector coordinates eliminate raster digitization error. Printed line widths and path simplification still limit meaningful plot comparison precision."},
        "figure2": {"pdf_page_one_based": 3, "method": "Manual literal transcription of every numbered element cell, checked against retained full-size publisher image.",
                    "n_numbered_elements": len(FIGURE2.splitlines()), "tolerance": 0,
                    "site_averaged_definition": "Per-element crystal count with complete corresponding L2 and L3 site-wise spectra.",
                    "site_wise_definition": "Either L2 or L3 spectrum for one absorbing site."},
        "figure5": {"pdf_page_one_based": 6, "format": "Raster-only overplot in source PDF.",
                    "restriction": "Opacity is not an empirical quantile, a class count, or a recoverable per-trace distribution. Preserve literal figure for comparative review; do not fabricate pointwise targets."},
    }
    (args.out/"provenance.json").write_text(json.dumps(provenance, indent=2)+"\n")
    print(json.dumps({"curves": 18, "vertices": len(traces), "figure2_elements": len(FIGURE2.splitlines())}))


if __name__ == "__main__":
    main()
