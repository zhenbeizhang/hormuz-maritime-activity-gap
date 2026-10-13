# Processed public inputs

This directory contains the compact, non-pixel inputs used by the public
reproduction workflow.

- `files/statistical_inputs/khor_fakkan_port_daily.csv`: 740 daily values in
  the fixed baseline, acute and recovery windows for 2022–2026.
- `files/statistical_inputs/no2_full_refit_daily_design.csv`: 2,718 daily
  records for the fixed 10, 20 and 30 km population-weighted NO2 domains,
  including predictors, coverage and eligibility fields.
- `files/analysis_ready/Supplementary_Data_5_acute_port_sar_robustness.csv`:
  delayed aggregate port/SAR sensitivity, detector agreement and spatial
  opportunity-baseline records; no vessel identity or exact coordinate.
- `files/main_figures/`, `files/supplementary_figures/` and
  `files/supplementary_tables/`: machine-readable display and table sources.

`SOURCE_DATA_INVENTORY.csv`, `FILE_MANIFEST.json` and `CHECKSUMS.sha256`
record dimensions and hashes. `FIGURE_TABLE_CROSSWALK.csv` maps key outputs to
their sources and public code.

These are transformed research inputs, not raw provider downloads. Raw
satellite pixels, meteorological grids, population rasters, PortWatch source
files and third-party model weights are excluded. See
`../docs/THIRD_PARTY_DATA.md` and `../DATA_RIGHTS.md`.
