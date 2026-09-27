#!/usr/bin/env python3
"""Independent controls for the literal published Figure 5 support comparison."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verifier",type=Path,required=True)
    p.add_argument("--truth",type=Path,required=True)
    p.add_argument("--candidate-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location("figure5_checked",a.verifier)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    ref=np.asarray(Image.open(a.truth/"figure5.png").convert("RGB"))
    contract=json.loads((a.truth/"figure5_comparison_contract.json").read_text())
    controls=[]
    def run(name,image,expected):
        r=module.compare(ref,image,contract)
        got=all(v["pass"] for x in r.values() for v in x.values())
        controls.append({"control":name,"expected_pass":expected,"actual_pass":got,
                         "control_pass":expected==got,
                         "passing_panel_colors":sum(v["pass"] for x in r.values() for v in x.values())})
    run("published_figure_against_itself",ref.copy(),True)
    run("empty_white_plot",np.full_like(ref,255),False)
    swapped=ref[:,:,[2,1,0]].copy()
    run("swap_red_blue_class_colors",swapped,False)
    missing=ref.copy();x0,y0,x1,y1=module.CALIBRATION["Cu"]["box"];missing[y0:y1,x0:x1]=255
    run("omit_Cu_panel",missing,False)
    flattened=ref.copy()
    for el in module.ELEMENTS:
        x0,y0,x1,y1=module.CALIBRATION[el]["box"]
        # Erase the spectral region after the first third of each energy axis,
        # which removes L2/post-edge features without altering class legend.
        flattened[y0:y1,x0+(x1-x0)//3:x1]=255
    run("remove_L2_and_postedge_features",flattened,False)
    applied=json.loads(a.candidate_report.read_text())
    report={"all_controls_pass":all(c["control_pass"] for c in controls),
        "controls":controls,"applied_candidate_paper_plot_pass":applied["paper_plot_pass"],
        "applied_candidate_passing_panel_colors":sum(v["pass"] for x in applied["panels"].values() for v in x.values()),
        "mandatory_panel_colors":16,
        "interpretation":"A candidate with a failed mandatory panel/color remains unvalidated. The checker uses an assumed, frozen renderer; absent author rendering parameters can make a scientific reconstruction fail this literal image gate. Failure must not be silently changed to acceptance or called proof of incorrect physics.",
        "review_findings":[
            "Distance-transform precision/recall and p90 checks implement the fixed contract separately for all sixteen panel/color pairs.",
            "The figure coordinate ticks were extracted independently of candidate data; no residual-driven masks are used.",
            "The blue dominance detector excludes some isolated faint paper pixels, e.g. RGB 251,252,254. Hence visible-color support still depends on compositing even though no density or class quantile is inferred.",
            "An Agg floor-compositing renderer can differ from the published raster's rounding. Any correction must be established from source-only calibration and recorded; tolerances may not be enlarged after inspecting candidate errors.",
            "Paper-plot comparison alone cannot certify code provenance, coordination assignments or honest construction of supplied arrays; independent source replay and scientific review remain mandatory."
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["all_controls_pass"] else 1)


if __name__=="__main__":main()
