# Third-party data and software

The repository redistributes derived research tables, not the large upstream
files listed below.

## IMF PortWatch

- Portal: https://portwatch.imf.org/
- Daily ports service: https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0
- Daily chokepoints service: https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0
- Terms: https://www.imf.org/en/about/copyright-and-terms

The study retains provider-defined aggregate values and identifies the
transformations used. The services are dynamic, so retrieval metadata and source
hashes should be preserved when repeating acquisition.

## Copernicus Sentinel products

- Copernicus Data Space: https://dataspace.copernicus.eu/
- Terms: https://dataspace.copernicus.eu/terms-and-conditions
- Attribution guidance: https://documentation.dataspace.copernicus.eu/FAQ.html

Sentinel-1 supplies SAR observations, Sentinel-2 supplies optical context and
Sentinel-5P supplies TROPOMI atmospheric products. The shared tables contain
derived values and selected product identifiers rather than raw imagery.
`data/files/supplementary_figures/Supplementary_Figure_2_source_data.csv`
records the exact Sentinel-1 product identifier, acquisition interval,
Sentinel-2 collection and composite period used for that contextual figure.
The corresponding project-authored analytical water is included as
`assets/khor_fakkan_research_water.geojson`; third-party image pixels are not
redistributed.

## ERA5

- Product access: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
- Licence: https://cds.climate.copernicus.eu/licences/licence-to-use-copernicus-products

Only derived meteorological-normalization fields are shared.

## GHS-POP

- Product: https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php
- Citation guidance: https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php
- Dataset DOI: https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE

Only derived population weights and coverage summaries are shared.

## xView3

- Code and model information: https://github.com/DIUx-xView/xView3_first_place
- Upstream release used: https://github.com/DIUx-xView/xView3_first_place/releases/tag/1.1
- Upstream source commit: `63a594601bf71a96909230d31097dca790b40ff2`
- Checkpoint file: `211117_00_11_b4_unet_s2_leaky_valid_4fold_rfl_soft_bce_mse_regularized_flips_light_medium_fold1.pth`
- Checkpoint SHA-256: `049059af337d6d85c14d26828708fc00258928736be9a2c2a2f8fc773dbfaa88`

Third-party code and weights are not included. The study uses public model
weights to construct vessel-like activity labels; those labels are not verified
vessel identities or an exhaustive vessel census.

## Independent YOLOv8n detector check

- Model repository: https://huggingface.co/MeWan2808/yolov8n-sar-vessel-detection
- Architecture: YOLOv8n
- Upstream-declared training data: SAR-Ship_Roboflow
- Upstream licence: MIT
- Weight-file SHA-256: `8c3b45950ec1c1d954c4a7a901744d8024b59be75684b92064da0a5a9c979297`

The downloaded public weights were applied without retraining or fine-tuning as
an independent detector cross-check on 12 Sentinel-1 scenes. The weights are not
redistributed. This comparison describes detector overlap under direct
application; it is not a ground-truth accuracy or recall estimate. No upstream
revision is stated because one was not recorded in the retained provenance.

## NASA FIRMS and Global Energy Monitor

- FIRMS: https://firms.modaps.eosdis.nasa.gov/
- FIRMS citation guidance: https://earthdata.nasa.gov/earth-observation-data/near-real-time/firms/citing-firms
- Global Energy Monitor downloads: https://globalenergymonitor.org/download-data/
- Global Energy Monitor licence: https://globalenergymonitor.org/creative-commons-public-license/

These sources provide contextual fire and fixed-facility information. Their
presence does not establish emission-source attribution.

## NOAA electronic navigational charts

- Access and public-use notices: https://www.nauticalcharts.noaa.gov/data/gis-data-and-services.html

No chart files are redistributed.
