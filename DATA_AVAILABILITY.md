# Data availability

Aggregate source data supporting the main and supplementary results are
available at https://github.com/zhenbeizhang/hormuz-maritime-activity-gap.
Version-specific reuse should cite the exact Git commit.

`article_data/` contains publication-facing source tables, a manifest and
SHA-256 checksums. `data/` contains compact processed inputs used to reproduce
the port moving-block bootstrap, validate delayed aggregate SAR records, and
run the population-weighted NO2 full-refit bootstrap. Shared vessel-like
activity is delayed and aggregate; no individual vessel identity or exact
detector coordinate is distributed.

Raw Sentinel-1/2 imagery, TROPOMI pixels, ERA5 grids, GHS-POP rasters, original
PortWatch downloads and third-party detector weights are not redistributed
because of volume and source-specific rights. Official access routes, product
identifiers and reuse conditions are documented in `docs/THIRD_PARTY_DATA.md`
and `DATA_RIGHTS.md`. The submitted Main Figure 2 and Supplementary Figure 2
include third-party image chips; the repository provides geometry, metadata,
derived values and provenance instead of the display pixels.
