# Statistical reproducibility

The public workflow separates core statistics that can be recomputed from
shared non-pixel inputs from displays that can only be redrawn from shared
source tables.

To run only the statistical checks:

```bash
python -m src.statistical_analysis --data-root data --output-root statistical_outputs
```

## Recomputed port–SAR comparison

The repository includes 435 daily IMF PortWatch observations for Khor Fakkan
(59 baseline and 28 acute-window days in each year from 2022 through 2026) and
96 eligible Sentinel-1 dates in the fixed 244.141701 km² adjacent-offshore
research water. The SAR input contains acquisition dates, relative orbits,
public Sentinel-1 product identifiers and project-derived vessel-like activity
densities.

`src/statistical_analysis.py` recomputes each year's baseline-to-acute change.
It then runs 5,000 bootstrap replicates with seed 20260817. PortWatch UTC days
are sampled within year and stage. SAR UTC dates are sampled within year,
stage and relative orbit. Historical extrema are reselected in every
replicate. The program verifies the point estimates and reported contrasts
against Supplementary Data 5.

The public input begins after scene matching: it does not reselect eligible SAR
dates from the full candidate-scene archive. Product identifiers and the fixed
matching parameters are retained so that this boundary is explicit.

## Recomputed May–June NO₂ comparison

The repository includes 3,624 daily aggregate records for four fixed
analytical domains and five years. Each row contains population-weighted
observed and expected tropospheric NO₂ columns, their anomaly, spatial and
population coverage, model reliability and the resulting eligibility flag.
Raw TROPOMI pixels, ERA5 grids and population rasters are not included.

The program reapplies one eligibility rule to every year, computes the 2026
May–June mean anomaly and the equal-weight mean of the 2022–2025 within-year
means, and reports their absolute difference in mol m⁻². Uncertainty uses
5,000 within-year UTC-week cluster bootstrap replicates for each analytical
domain. Recomputed results are checked against the shared May–June summary.

## Not recomputed from raw observations

The public workflow does not acquire or preprocess satellite pixels, rerun
xView3 inference, fit the meteorological expectation model or reconstruct
population weights. It also does not repeat SAR eligible-date selection from the
complete candidate archive. Other supplementary statistics are checked as
shared source-table values and used to redraw displays; they are not presented
as end-to-end raw-data reproduction.

All parameters, eligibility rules, seeds and source links are in
`data/files/statistical_inputs/`. Source-specific reuse terms continue to apply
to provider-derived values; see `DATA_RIGHTS.md`.
