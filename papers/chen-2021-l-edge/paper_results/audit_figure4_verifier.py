#!/usr/bin/env python3
"""Positive and adversarial controls for the direct published-curve verifier."""
import argparse
import copy
import csv
import json
import tempfile
from pathlib import Path

import numpy as np

from verify_figure4 import verify


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--truth", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a=p.parse_args()
    original=list(csv.DictReader((a.candidate/"figure4_reconstruction.csv").open()))
    meta=json.loads((a.candidate/"figure4_provenance.json").read_text())
    results=[]
    def run(name, mutate, expected=False):
        rows,m=copy.deepcopy(original),copy.deepcopy(meta)
        changed=mutate(rows,m)
        if changed is not None:rows=changed
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            with (d/"curve.csv").open("w") as f:
                w=csv.DictWriter(f,list(original[0]));w.writeheader();w.writerows(rows)
            (d/"meta.json").write_text(json.dumps(m))
            r=verify(d/"curve.csv",d/"meta.json",a.truth)
        got=r["paper_numerical_pass"]
        results.append({"control":name,"expected_paper_numerical_pass":expected,
                        "actual_paper_numerical_pass":got,"control_pass":got==expected,
                        "errors":{k:v["errors"] for k,v in r["panels"].items()}})
    def y_transform(f):
        def change(rows,meta):
            for r in rows:r["intensity"]=str(f(float(r["energy_eV"]),float(r["intensity"]),r["material"]))
        return change
    def x_transform(f):
        def change(rows,meta):
            for r in rows:r["energy_eV"]=str(f(float(r["energy_eV"]),r["material"]))
        return change
    def mutate_metadata(key,value):
        def change(rows,m):m["MgMn2O4"][key]=value
        return change
    run("unaltered_candidate",lambda r,m:None,True)
    run("permitted_rigid_translation",x_transform(lambda x,m:x+1.7),True)
    run("missing_required_material",lambda r,m:[v for v in r if v["material"]!="LiFePO4"])
    run("all_zero",y_transform(lambda x,y,m:0))
    run("constant_unit_response",y_transform(lambda x,y,m:1))
    run("permitted_native_intensity_units",y_transform(lambda x,y,m:y*.6),True)
    run("unphysical_not_finite",y_transform(lambda x,y,m:float("nan") if m=="MgMn2O4" else y))
    run("negative_energy_axis",x_transform(lambda x,m:-x))
    run("missing_L2_feature",y_transform(lambda x,y,m:0.05 if m=="MgMn2O4" and 650<x<660 else y))
    run("independent_L2_displacement",x_transform(lambda x,m:x+1 if m=="MgMn2O4" and x>650 else x))
    run("energy_axis_stretched",x_transform(lambda x,m:642+(x-642)*1.08 if m=="MgMn2O4" else x))
    run("clipped_postedge",lambda r,m:[v for v in r if v["material"]!="MgMn2O4" or float(v["energy_eV"])<660])
    run("clipped_preedge",lambda r,m:[v for v in r if v["material"]!="MgMn2O4" or float(v["energy_eV"])>642])
    run("spurious_postedge_plateau",y_transform(lambda x,y,m:0.7 if m=="MgMn2O4" and x>660 else y))
    run("wrong_material_id",mutate_metadata("material_id","mp-0"))
    run("wrong_absorber",mutate_metadata("element","Fe"))
    run("forged_source_identifiers",mutate_metadata("source_record_ids",["fabricated-L2","fabricated-L3"]))
    run("duplicated_source_identifier",mutate_metadata("source_record_ids",["mp-32006-2-XANES-L2"]*2))
    run("wrong_broadening",mutate_metadata("broadening_fwhm_eV",2.0))
    run("preapplied_declared_registration",mutate_metadata("energy_shift_eV",1.0))
    report={"all_controls_pass":all(r["control_pass"] for r in results),
            "n_controls":len(results),"n_expected_rejections":sum(not r["expected_paper_numerical_pass"] for r in results),
            "controls":results,
            "scope":"This audit tests strict paper-curve checks, not whether an arbitrary submitted program honestly produced its arrays. Independent source/code execution remains required."}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="controls"},indent=2))
    raise SystemExit(0 if report["all_controls_pass"] else 1)


if __name__=="__main__":main()
