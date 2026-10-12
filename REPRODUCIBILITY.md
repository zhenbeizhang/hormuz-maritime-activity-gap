# Reproducibility

## One-command workflow

From the repository root, run:

```bash
python reproduce_all.py --data-root data --output-root reproduced_outputs
```

The command validates the compact workflow data directory, recomputes the
reported port–SAR and May–June NO₂ statistics, redraws eight computational
figures, validates the provenance record for the optical/SAR context panel,
validates eleven supplementary tables and writes checksums, logs and a
machine-readable output manifest. It performs no network requests. The
publication-facing Article tables are separately indexed under
`article_data/`.

## Reproduced outputs

- two graphical composites used to verify the Article's regional and focal
  time-series results;
- Supplementary Figures 1 and 3–7;
- provenance validation for the withheld Supplementary Figure 2 display;
- Supplementary Tables 1–11;
- five-year port–SAR point estimates and stratified bootstrap intervals;
- May–June population-weighted NO₂ absolute differences and UTC-week cluster
  bootstrap intervals for the four fixed analytical domains;
- copies of all figure source-data tables;
- input and output validation summaries.

The statistical workflow verifies its recomputed values against the shared
Supplementary Data 5 and NO₂ summary table. Public parameters, resampling
units, seeds, eligibility rules and analytical-domain definitions are stored
under `data/files/statistical_inputs/`.

## Operations outside this lightweight workflow

- satellite-data acquisition and preprocessing;
- Earth Engine operations;
- xView3 model inference or training;
- meteorological normalization and population weighting;
- third-party API access.

Statistics outside the two declared core recomputations remain available as
shared source-table values for display verification rather than full upstream
re-estimation. Current manuscript numbering and source tables are indexed under
`article_data/`; internal lightweight figure filenames identify verification
composites rather than final submission figures. The complete submitted Main
Figure 2 and Supplementary Figure 2 are excluded from full public rendering
because their third-party optical/SAR pixel chips are not redistributed.

## Determinism

Figure dimensions, style parameters, SVG hash salts and PDF metadata are fixed.
The test suite checks input integrity, expected output counts, relative paths
and the absence of credentials. Small rasterization differences can occur when
the environment differs from `environment.yml`; scientific values and vector
geometry must remain unchanged.
