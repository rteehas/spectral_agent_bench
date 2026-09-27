#!/usr/bin/env python3
"""Independent, source-only regression for Figure 5 stroke-width calibration.

Inputs are solely the published PNG. This compares the already proposed 1.65px
correction with the original 1px renderer and never reads a candidate ensemble.
"""
import argparse
import hashlib
import json

import numpy as np
from PIL import Image
from scipy.signal import savgol_filter
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--figure",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    image=np.asarray(Image.open(a.figure).convert("RGB"),dtype=float)
    crop=image[140:240,1230:1350]
    contrast=255-crop[:,:,1]
    positions=np.arange(100,dtype=float)[:,None]
    centers=(contrast*positions).sum(axis=0)/contrast.sum(axis=0)
    centers=savgol_filter(centers,5,2)
    fig=Figure(figsize=(1.2,1),dpi=100);canvas=FigureCanvasAgg(fig)
    ax=fig.add_axes([0,0,1,1]);ax.set_axis_off();ax.set_xlim(-.5,119.5);ax.set_ylim(99.5,-.5)
    line,=ax.plot(np.arange(120),centers,color="#e41a1c",alpha=.015,solid_capstyle="round")
    scores={}
    for width in [1.0,1.65]:
        line.set_linewidth(width*72/100);canvas.draw()
        rendered=np.asarray(canvas.buffer_rgba())[:,:,:3].astype(float)
        scores[str(width)]={}
        for name,sl in [("whole_interior",slice(5,115)),("left_profile",slice(5,60)),("right_profile",slice(60,115))]:
            scores[str(width)][name]=float(np.sqrt(np.mean((rendered[:,sl]-crop[:,sl])**2)))
    # Independent nearly horizontal cross-sections near the isolated arc's
    # stationary point; their integrated width also exceeds the 1px assumption.
    profiles=[]
    for x in [1273,1274,1275,1276,1277]:
        col=255-image[175:215,x,1]
        peak=float(col.max())
        profiles.append({"source_x":x,"nonwhite_y_coordinates":[int(y+175) for y in np.flatnonzero(col)],
                         "green_contrasts":[float(v) for v in col[col>0]],
                         "integrated_contrast_over_peak_pixels":float(col.sum()/peak)})
    report={"source_only":True,"candidate_arrays_or_images_read":False,
        "source_figure_sha256":hashlib.sha256(open(a.figure,"rb").read()).hexdigest(),
        "source_crop":[1230,140,1350,240],"fixed_opacity":.015,
        "original_width_source_pixels":1.0,"proposed_corrected_width_source_pixels":1.65,
        "comparison":scores,"independent_nearly_horizontal_profiles":profiles,
        "correction_supported":all(scores["1.65"][k]<scores["1.0"][k] for k in scores["1.0"]),
        "scope":"Supports replacing an inaccurate stroke-width calibration, not changing scientific tolerances, coordinates, class labels, spectral curves or opacity. The original failed candidate result must be retained. No claim that the author's entire renderer is recovered."}
    open(a.out,"w").write(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["correction_supported"] else 1)


if __name__=="__main__":main()
