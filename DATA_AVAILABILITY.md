# Data availability

The aggregate source data supporting the main figures, supplementary figures
and supplementary tables are available in this GitHub repository:
https://github.com/zhenbeizhang/hormuz-maritime-activity-gap.

Version-specific reuse should cite the full Git commit URL used for the
analysis.

The `article_data/` directory contains the publication-facing source tables for
all four main figures, seven supplementary figures, eleven supplementary tables
and five Supplementary Data files, with a manifest and SHA-256 checksums. The
`data/` directory additionally contains the compact fixed daily PortWatch
values, eligible-date SAR activity proxies and population-weighted daily NO₂
aggregates used to independently recompute the core contrasts and bootstrap
intervals. These are transformed analytical inputs, not raw provider files.
Because of volume and source-specific redistribution conditions, the repository does not duplicate
raw Sentinel-1 or Sentinel-2 imagery, TROPOMI pixel stacks, ERA5 grids, GHS-POP
rasters or third-party xView3 weights. Official access routes and source
identifiers are documented in `docs/THIRD_PARTY_DATA.md`.

The complete display assets for submitted Main Figure 2 and Supplementary
Figure 2 are not stored in the public repository because their optical and SAR
pixel chips are not redistributed. The repository supplies the associated
analytical geometry, derived scores, automatic method-comparison values,
product identifiers, dates and official access URLs, and records the pixel
panels as documented exceptions.

Port-call and passage indicators were obtained from IMF PortWatch. Shared tables
identify the source and preserve the transformations used in the study. Reuse
of provider-derived values remains subject to the applicable provider terms.
