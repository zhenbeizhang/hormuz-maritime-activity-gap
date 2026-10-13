# Spatial observations of the 2026 Hormuz disruption

This repository contains source data and analysis code for the Article
**“Spatial observations expose limits of monitoring the Hormuz disruption
through port records.”** The study compares provider-defined port calls,
Sentinel-1/xView3-derived vessel-like activity in fixed adjacent-water research
geometries, and population-weighted TROPOMI tropospheric NO2 column anomalies.

The evidence is aggregate and delayed. It does not disclose individual vessel
identities or positions, infer port substitution, attribute atmospheric
anomalies to ships, or convert tropospheric columns into surface concentrations,
personal exposure or health effects.

## Repository map

- `article_data/`: publication-facing source data for the main and
  supplementary displays, eleven supplementary tables and five Supplementary
  Data files.
- `data/`: compact processed inputs for the public statistical workflow.
- `src/analysis/port_sar_uncertainty.py`: port moving-block bootstrap and
  validation of delayed aggregate SAR robustness records.
- `src/analysis/no2_full_refit_bootstrap.py`: full-refit moving-block bootstrap,
  diagnostics and coverage checks for three fixed NO2 domains.
- `src/figures/article_figures.py`: deterministic analytical verification
  renders for the Figure 3 and Figure 4 source tables.
- `tests/`: numerical, data-contract and repository-integrity tests.

## Run

```bash
conda env create -f environment.yml
conda activate hormuz-maritime-reproduction
python -m pytest -q
python reproduce_all.py --data-root data --article-data article_data --output-root reproduced_outputs
```

The full workflow uses 5,000 bootstrap replicates for each prespecified block
length. For a quick installation check, pass `--replicates 10`; that smoke run
does not reproduce publication intervals.

The workflow reproduces the port estimates and intervals, validates aggregate
SAR detector/opportunity records, refits the NO2 model within every bootstrap
replicate, reports leave-one-year-out diagnostics, and creates verification
plots from shared source tables. It does not download raw data or rerun
satellite preprocessing and model inference.

## Public evidence boundary

The repository distributes delayed aggregate vessel-like activity, not
coordinate-level detector outputs. Raw Sentinel imagery, TROPOMI pixels, ERA5
grids, GHS-POP rasters, PortWatch provider downloads and third-party model
weights are excluded. Access routes and reuse conditions are documented in
[`docs/THIRD_PARTY_DATA.md`](docs/THIRD_PARTY_DATA.md) and
[`DATA_RIGHTS.md`](DATA_RIGHTS.md).

Main Figure 2 and Supplementary Figure 2 contain third-party image chips in the
submitted manuscript. The repository provides their analytical geometry,
display metadata, derived measurements and provenance, but not the pixels.
Public figure outputs are analytical verification renders rather than
pixel-identical journal layouts.

## Citation and reuse

Use `CITATION.cff` and cite the exact Git commit used for an analysis. The MIT
licence applies only to project-authored software; it does not relicense data,
imagery, model weights or provider-derived values.
