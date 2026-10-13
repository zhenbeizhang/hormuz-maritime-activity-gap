# Article source data

This directory indexes publication-facing source data for **“Spatial
observations expose limits of monitoring the Hormuz disruption through port
records.”**

- `main_figures/`: source tables and analytical geometry for Figures 1–4.
- `supplementary_figures/`: source tables for Supplementary Figures 1–7.
- `supplementary_tables/`: eleven machine-readable supplementary tables.
- `supplementary_data/`: five Supplementary Data files.
- `MANIFEST.csv` and `CHECKSUMS.sha256`: dimensions and SHA-256 integrity
  records.

Main Figure 2 is represented by a geometry file, display metadata and panels
c–d source table because third-party optical/SAR pixels are not redistributed.
Supplementary Data 5 is the current acute port/SAR robustness table; the
earlier joint-extremeness table is superseded and is not part of this package.

PortWatch values are provider-defined calls or passages. SAR outputs are
delayed aggregate vessel-like activity, not verified individual vessels. NO2
values are population-weighted tropospheric-column anomalies and do not
identify a source or measure surface exposure. Access and reuse conditions are
documented in `../docs/THIRD_PARTY_DATA.md` and `../DATA_RIGHTS.md`.
