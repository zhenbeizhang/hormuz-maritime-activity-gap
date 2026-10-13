# Reproducibility

From the repository root:

```bash
python -m pytest -q
python reproduce_all.py --data-root data --article-data article_data --output-root reproduced_outputs
```

The one-command workflow performs no network requests. It recomputes the port
circular moving-block bootstrap, validates delayed aggregate SAR robustness
and detector-opportunity records, runs the population-weighted NO2 full-refit
moving-block bootstrap with leave-one-year-out diagnostics, and produces
analytical verification renders for Figures 3 and 4.

The publication run uses 5,000 replicates at the primary 7-day block length and
the 5- and 14-day sensitivities. A smaller `--replicates` value is available
only as an installation smoke test.

Raw provider downloads, satellite pixels, coordinate-level detector outputs,
third-party model weights and the upstream preprocessing chain are outside the
public package. Accordingly, the public workflow validates aggregate results
from the detector comparison and spatial opportunity baseline but does not
rerun the coordinate-level null. Main Figure 2 and Supplementary Figure 2 are
represented by geometry, metadata, derived values and provenance because their
third-party image chips are not redistributed.

See `docs/STATISTICAL_REPRODUCIBILITY.md` for estimators and inputs,
`docs/THIRD_PARTY_DATA.md` for access routes, and `DATA_RIGHTS.md` for reuse
conditions.
