# Data availability

The aggregate source data supporting the main figures, supplementary figures
and supplementary tables are available in this GitHub repository:
https://github.com/zhenbeizhang/hormuz-maritime-activity-gap.

An immutable study snapshot should be cited using the full Git commit URL that
corresponds to the submitted manuscript.

The repository includes figure-source CSV files, analysis-ready aggregate
tables, a data dictionary, source documentation, manifests and SHA-256
checksums. It also includes the fixed daily PortWatch values, eligible-date SAR
activity proxies and population-weighted daily NO₂ aggregates used to
recompute the reported core contrasts and bootstrap intervals. These are
transformed analytical inputs, not raw provider files. Because of volume and
source-specific redistribution conditions, the repository does not duplicate
raw Sentinel-1 or Sentinel-2 imagery, TROPOMI pixel stacks, ERA5 grids, GHS-POP
rasters or third-party xView3 weights. Official access routes and source
identifiers are documented in `docs/THIRD_PARTY_DATA.md`.

The display asset for Supplementary Figure 2 is not stored in the public
repository before acceptance because its optical and SAR pixel chips are not
redistributed. The repository supplies its analytical geometry, product
identifiers, dates and official access URLs, and the lightweight workflow
records the panel as withheld rather than claiming to reconstruct it.

Port-call and passage indicators were obtained from IMF PortWatch. Shared tables
identify the source and preserve the transformations used in the study. Reuse
of provider-derived values remains subject to the applicable provider terms.
