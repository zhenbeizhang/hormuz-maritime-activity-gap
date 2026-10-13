# Statistical reproducibility

The public workflow starts from processed, non-pixel inputs. It reproduces core
reported statistics without downloading restricted or very large products.

## Port and aggregate SAR

```bash
python -m src.analysis.port_sar_uncertainty --data-root data --output-root reproduced_outputs/port_sar
```

The input contains 740 fixed-window Khor Fakkan daily values: 59 baseline, 28
acute and 61 recovery days for each year from 2022 through 2026. The program
computes port contrasts and 5,000 circular moving-block bootstrap replicates at
the prespecified 7-day block length, with 5- and 14-day sensitivity analyses.
Historical extrema are reselected within each replicate. It also verifies the
delayed aggregate SAR sensitivity and detector-opportunity records in current
Supplementary Data 5.

The public package does not contain coordinate-level detector outputs or input
GeoTIFFs. Consequently it validates, but does not rerun, the coordinate-level
spatial opportunity null. Pure one-to-one matching and rigid-shift functions
are public and tested.

## Population-weighted NO2

```bash
python -m src.analysis.no2_full_refit_bootstrap --input data/files/statistical_inputs/no2_full_refit_daily_design.csv --output-root reproduced_outputs/no2
```

The input contains 906 daily rows for each fixed 10, 20 and 30 km domain. Each
bootstrap replicate resamples daily blocks, refits the fixed historical OLS
design, repeats leave-one-year-out prediction for the historical comparison,
and preserves eligibility and coverage. The primary block length is 7 days,
with 5- and 14-day sensitivities and 5,000 replicates per domain and block.
Outputs include intervals, model diagnostics and population-coverage summaries.

The atmospheric quantity is a population-weighted tropospheric NO2 column
anomaly. It is not a source-attribution, surface-concentration, personal-
exposure, health-effect or causal estimate.

## Figure verification and tests

```bash
python -m src.figures.article_figures --article-data article_data --output-root reproduced_outputs/figures
python -m pytest -q
```

The figure program redraws analytical verification views from Figure 3 and
Figure 4 source tables. It does not reproduce third-party pixel chips or the
editorial journal layout.
