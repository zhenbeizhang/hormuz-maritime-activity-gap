# Source data

This directory contains the shareable tabular data used by the lightweight
reproduction workflow.

## Contents

- `files/main_figures/`: source tables for Main Figures 1 and 2.
- `files/supplementary_figures/`: source tables for Supplementary Figures 1–7.
- `files/supplementary_tables/`: Supplementary Tables 1–10.
- `files/analysis_ready/`: five supplementary datasets plus compact supporting
  timelines used to document the focal comparison and sensitivity analyses.
- `FIELD_DICTIONARY.csv`: field-level names, types, units and missing-value
  semantics.
- `SOURCE_DATA_INVENTORY.csv`: row counts, column counts, file sizes and hashes.
- `FIGURE_TABLE_CROSSWALK.csv`: mapping from displayed items to source files and
  plotting code.
- `FILE_MANIFEST.json` and `CHECKSUMS.sha256`: integrity records.

## Interpretation boundaries

- SAR vessel-like labels are a relative activity proxy, not verified vessel
  totals or individual vessel identities.
- PortWatch values are provider-defined calls or passages, not customs
  throughput or an exhaustive physical census.
- NO₂ values are population-weighted tropospheric-column anomalies, not surface
  concentrations, personal exposure or health effects.
- Empty fields mean missing or inapplicable under the source table's contract;
  numeric zero remains an observed zero unless a named field states otherwise.
  Supplementary Data 1 additionally uses the literal sentinel
  `not_available` for quantities absent from the source analysis; the sentinel
  never represents zero. Its unique row key is
  `evidence_record_id` + `analysis_window` + `comparison_definition`.

Raw satellite imagery, atmospheric pixel stacks, meteorological grids,
population rasters and model weights are not included. See
`../docs/THIRD_PARTY_DATA.md` for official access routes.

`files/statistical_inputs/` contains the smallest non-pixel inputs used by the
public statistical workflow: fixed daily PortWatch calls, eligible-date SAR
activity densities, population-weighted daily NO₂ aggregates, fixed parameters
and shared summaries used for independent equality checks. The NO₂ daily table
contains coverage and eligibility flags so that one rule can be reapplied to
all five years.
