# Worked candidate execution notes

The worked candidate was implemented and executed by the `worked_execution` agent. It reads only the eight native-record gzip files; it does not read published plots, historical labels, reference spectra, held-back summaries, verifier code or prior candidate outputs.

The final run used a fresh export:

```bash
/tmp/chen-bench-env/bin/python papers/chen-2021-l-edge/export_agent_bundle.py Q1 --output /tmp/chen-worked/final-agent
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/chen-final-mpl \
  /tmp/chen-bench-env/bin/python docs/data/chen-2021-l-edge/workflows/candidate.py all \
  --inputs /tmp/chen-worked/final-agent/inputs --output /tmp/chen-worked/final
```

The three questions have identical raw inputs. The `all` invocation shares raw parsing and coordinate calculations, then independently emits each task's complete artifacts. Any one task can be executed separately with `Q1`, `Q2` or `Q3` and a direct output directory. Dependencies are pinned in `requirements.txt` and `requirements-lock.txt`.

All three analyses completed successfully. The final run parsed 27,570 raw observations from 7,618 materials. Q1 emitted 15,792 complete material/element/edge responses, excluding 386 groups; Q2 used 13,589 valid paired sites; Q3 evaluated 5,408 regular-geometry sites from 3,602 materials and 3,339 reduced compositions. Optional-site metadata differences do not cause exclusions; the true `mp-12905` structure collision is excluded throughout. Native `mvc` source names are preserved. Negative spectral values, missing paired edges and missing inequivalent-site coverage are explicitly audited.

The geometry search radius was independently checked against every derived nearest distance: the maximum radius needed by the loosest 1.25-times-nearest-distance definition is 4.547 Å, below the 6 Å search radius. Tetrahedral labels require angular geometry and radial consistency rather than merely CN=4. Figures were visually inspected for usable axes, legends and representative spectra. spglib emits a small number of C-library warnings during alternate symmetry-tolerance calculations; failed alternate searches are recorded and do not produce fabricated equivalence classes.

The scientific results are intentionally not all positive. Exact-composition Q2 overlap is only 301 sites across 108 materials and 76 element/composition strata, and the nominal contrast interval includes zero. The broader element/ligand-adjusted association is more precise but does not establish a composition-invariant geometry effect. Q3 L2 increments are small and paired intervals overlap zero at both tested resolutions. These limitations are in the reports and do not cause benchmark failure.

This file records the implementation-side execution. `workflow_execution_review.md` records the separate fresh replay; the independent verifier and mutation audit provide a separate numerical integrity check. Candidate choices are illustrative, not additional solver-facing instructions or required methods.
