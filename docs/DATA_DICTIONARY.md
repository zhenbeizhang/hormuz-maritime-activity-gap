# Data dictionary guide

The machine-readable field dictionary is available at
`data/FIELD_DICTIONARY.csv`. Each record contains:

| Field | Meaning |
|---|---|
| `file` | Repository-relative source-table path |
| `field` | Column name |
| `storage_type` | Declared storage type |
| `unit` | Unit or source-native semantic |
| `missing_value_semantics` | Interpretation of blank or null values |
| `description` | Field description or interpretation boundary |

## Missing values and row keys

Blank cells are missing or inapplicable unless a field-level record states a
more specific meaning. In `Supplementary_Data_1_full_evidence_matrix.csv`, the
literal value `not_available` is an explicit missing-value sentinel: the
quantity was not available for that source analysis and must not be interpreted
as zero. The three fields `evidence_record_id`,
`analysis_window` and `comparison_definition` form the unique row key;
`evidence_record_id` alone identifies an evidence family and may repeat.

## Principal measurement families

### PortWatch

Fields beginning with `portwatch_` or `port_` describe provider-defined port
calls or passages. Daily values and fixed-window summaries retain their native
count or count-per-day units. Historical comparisons use the same calendar
period in 2022–2025 unless the field states otherwise.

### Sentinel-1/xView3 activity proxy

Fields beginning with `sar_` describe retained vessel-like labels, eligible
scene counts, research-water area or density per 100 km². The labels are used as
a relative activity proxy. They are not an exhaustive vessel census.

### TROPOMI NO₂

Fields beginning with `no2_` describe tropospheric-column anomalies in mol m⁻²,
valid-day coverage, historical comparisons or bootstrap intervals. Population-
weighted burden fields preserve their declared person–mol m⁻² units and must
not be interpreted as dose or health burden.

### Validation and sensitivity fields

Coverage, detector-overlap, independent-model, manual-review and sensitivity
fields document limits on interpretation. Different validation summaries use
different denominators and should not be combined into a single accuracy score.

### Public statistical inputs

Files under `data/files/statistical_inputs/` contain daily or eligible-date
aggregates rather than raw provider files or satellite pixels. Their composite
keys are `date_utc + year + analysis_stage` for the port and SAR inputs and
`analysis_id + buffer_km + utc_date` for the daily NO₂ input. The accompanying
JSON files define fixed windows, domains, eligibility rules, estimators,
resampling units and seeds.
