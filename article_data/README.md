# Article source data

This directory contains the publication-facing source tables for the Article
**“Spatial observations expose limits of monitoring the Hormuz disruption
through port records.”** It is the source-data index corresponding to the
submitted manuscript and Supplementary Information.

## Contents

- `main_figures/`: source tables for Main Figures 1–4, the nitrogen-dioxide
  pixel map and Main Table 1.
- `supplementary_figures/`: source tables for Supplementary Figures 1–7.
- `supplementary_tables/`: Supplementary Tables 1–10 in machine-readable form.
- `supplementary_data/`: the five Supplementary Data files supplied with the
  Article.
- `MANIFEST.csv` and `CHECKSUMS.sha256`: file dimensions and integrity records.

Display-ready journal figures are intentionally not stored here. They are
embedded in the submission manuscript and can be generated from the shared
tables and project code, except for the optical and SAR pixel-chip panel whose
third-party pixels are not redistributed.

## Interpretation boundaries

- PortWatch records are provider-defined calls or passages.
- SAR vessel-like labels are a relative activity proxy, not verified vessel
  totals or individual vessel identities.
- Nitrogen-dioxide values are tropospheric-column anomalies, not surface
  concentrations, personal exposure or health outcomes.
- The Khor Fakkan focal case was selected after the regional screen.
- The atmospheric results do not identify a shipping, port or industrial
  source.

Raw imagery, atmospheric pixel stacks, meteorological grids, population
rasters and third-party model weights are not redistributed. Official access
routes and source-specific conditions are documented in
`../docs/THIRD_PARTY_DATA.md`.
