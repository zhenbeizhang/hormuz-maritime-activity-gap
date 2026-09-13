# Khor Fakkan port calls diverged from adjacent-water activity

This repository contains the source data and plotting code associated with the
study **“Khor Fakkan port calls diverged from adjacent-water activity.”** The
study compares provider-recorded port calls with a
Sentinel-1/xView3-derived vessel-activity proxy in fixed adjacent-offshore
research waters and with population-weighted TROPOMI tropospheric NO₂ column
anomalies.

The repository supports a bounded measurement result. It does not identify
individual vessel movements, establish port substitution, estimate causal
effects, attribute atmospheric anomalies to ships, or convert tropospheric NO₂
columns into surface concentration, personal exposure or health outcomes.

## Repository contents

- `data/`: source tables for two main figures, seven supplementary figures,
  ten supplementary tables, five supplementary datasets and the aggregate
  daily inputs needed for the reported port–SAR and May–June NO₂ statistics.
- `src/`: statistical analysis, plotting, validation and output utilities.
- `assets/`: project-authored analytical geometry and regional land context
  used by plotting and provenance records.
- `tests/`: automated checks for inputs, outputs, paths and sensitive content.
- `docs/`: data-source, field and redistribution documentation.

The exact statistical boundary is described in
[`docs/STATISTICAL_REPRODUCIBILITY.md`](docs/STATISTICAL_REPRODUCIBILITY.md).

Display-ready manuscript figures are intentionally not version-controlled
before journal acceptance. They are generated locally from the shared source
tables and plotting code. The optical/SAR chip panel in Supplementary Figure 2
is recorded as withheld because its third-party pixel chips are not
redistributed.

## Reproduce the figures and tables

Create the declared environment and run the repository-level command:

```bash
conda env create -f environment.yml
conda activate hormuz-maritime-reproduction
python reproduce_all.py --data-root data --output-root reproduced_outputs
```

The command generates:

- two main figures and six of the seven supplementary figures in PDF,
  SVG and PNG;
- the five-year port–SAR point estimates and 5,000-replicate stratified
  bootstrap;
- the May–June population-weighted NO₂ absolute differences and 5,000-
  replicate UTC-week cluster bootstrap for four fixed analytical domains;
- 600-dpi PNG copies and a generated-output checksum inventory;
- validated copies of ten supplementary tables;
- copied figure source data, checksums, a run log and a machine-readable output
  manifest.

The output directory must be absent or empty. The workflow fails if a required
file, checksum, table schema or declared source-data shape has changed.

## Reproducibility boundary

This workflow recomputes the reported core contrasts from shared, non-pixel
inputs and redraws figures from aggregate and scene-level tables. It does not
download imagery, call Earth Engine, rerun xView3 inference, reconstruct
population weights or repeat the upstream TROPOMI/ERA5 processing. The shared
NO₂ daily input contains population-weighted aggregate values, coverage and
eligibility fields, not raw pixels.

Supplementary Figure 2 is not rendered by the public package before acceptance
because its underlying optical and SAR pixel chips are not redistributed. Its
source table documents geometry and imagery lineage, and the run manifest
records the panel as withheld rather than silently substituting a placeholder.

## Data sources and interpretation

The analysis uses IMF PortWatch, Copernicus Sentinel-1/2/5P, ERA5, GHS-POP,
the public xView3 model family and a separately published YOLOv8n detector for
an independent 12-scene cross-check. Raw provider files and third-party model
weights are not redistributed. See [third-party data documentation](docs/THIRD_PARTY_DATA.md)
and [data rights](DATA_RIGHTS.md) for access routes, attribution and reuse
boundaries.

Vessel-like labels are a relative remote-sensing activity proxy rather than a
verified vessel census. PortWatch values are provider-defined calls or passages.
NO₂ values are population-weighted tropospheric-column anomalies. These domains
retain different units, denominators and sampling frequencies.

## Citation

Use the repository citation in `CITATION.cff` and cite the associated article
when it becomes available. Cite the full Git commit URL used for an analysis,
because the `main` branch may continue to change.

## Licence and reuse

Project-authored software code is available under the scoped MIT License in
`LICENSE`. The licence does not cover data, manuscript figures, satellite
imagery, model weights or provider-derived values. See `DATA_RIGHTS.md` for
source-specific rights and reuse boundaries.
