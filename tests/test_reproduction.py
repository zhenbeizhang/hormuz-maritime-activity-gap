from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

from reproduce_all import reproduce
from src.common import security_scan, validate_data_package
from src.statistical_analysis import reproduce as reproduce_statistics


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"


def test_source_data_passes_integrity_checks() -> None:
    result = validate_data_package(DATA_ROOT)
    assert result["checksum_errors"] == []
    assert result["canonical_member_count"] > 0
    assert len(result["shapes"]) == 23


def test_modified_source_data_is_rejected(tmp_path: Path) -> None:
    copied = tmp_path / "data"
    shutil.copytree(DATA_ROOT, copied)
    target = copied / "files/main_figures/Figure_1_source_data.csv"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum failure"):
        validate_data_package(copied)


def test_missing_source_data_is_rejected(tmp_path: Path) -> None:
    copied = tmp_path / "data"
    shutil.copytree(DATA_ROOT, copied)
    target = copied / "files/supplementary_figures/Supplementary_Figure_7_source_data.csv"
    target.unlink()
    with pytest.raises(FileNotFoundError, match="Required source-data input missing"):
        validate_data_package(copied)


def test_repository_security_scan_is_clean() -> None:
    assert security_scan(ROOT) == []


def test_public_repository_contains_no_internal_workflow_markers() -> None:
    fixed_word = "fro" + "zen"
    patterns = {
        "legacy fixed-result sentinel": re.compile(
            "not_available_in_" + fixed_word + "_result", re.IGNORECASE
        ),
        "legacy fixed-field suffix": re.compile(
            rf"\b[A-Za-z0-9_]+_{fixed_word}\b", re.IGNORECASE
        ),
        "legacy fixed wording": re.compile(rf"\b{fixed_word}\b", re.IGNORECASE),
        "numbered decision identifier": re.compile(
            r"(?<![A-Z0-9])D-\d{3}(?![A-Z0-9])", re.IGNORECASE
        ),
        "numbered execution role": re.compile(
            r"\brole[ _-]?0?\d+\b", re.IGNORECASE
        ),
        "numbered workflow gate": re.compile(
            r"\bgate[ _-]?\d+\b", re.IGNORECASE
        ),
        "numbered workflow stage": re.compile(
            r"\bstage[ _-]?\d+\b", re.IGNORECASE
        ),
        "internal governance field": re.compile(
            "formal_scientific_" + r"results_allowed|region_" + r"role_d\d+",
            re.IGNORECASE,
        ),
        "internal staff role": re.compile(
            r"chief[_ -]?" + "scientist|research[_ -]?" + "lead|adversarial[_ -]?" + "reviewer",
            re.IGNORECASE,
        ),
        "internal assistant name": re.compile(
            r"\b(?:Code" + "x|Chat" + "GPT|Open" + r"AI)\b", re.IGNORECASE
        ),
        "execution-status residue": re.compile(
            r"\b(?:not_" + "executed|trial_" + r"failed)\b", re.IGNORECASE
        ),
        "legacy analysis-workflow label": re.compile(
            r"\b(?:shipping_" + "module|environmental_" + "pilot|no_formal_"
            + "outcome|discovery_focal_" + "case|post_result_focal_" + "case)\b",
            re.IGNORECASE,
        ),
        "legacy candidate-table field": re.compile(
            r"\b(?:initial_analytical_" + "role|current_reporting_" + "role)\b",
            re.IGNORECASE,
        ),
        "unsupported late-phase label": re.compile(
            r"\breco" + r"very\b", re.IGNORECASE
        ),
        "internal version label": re.compile(
            r"(?<![A-Za-z0-9])v(?:0|1|4)(?:[._-]\d+)*(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    }
    suffixes = {".cff", ".csv", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
    findings: list[tuple[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in suffixes:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append((path.relative_to(ROOT).as_posix(), label))
    assert findings == []


def test_documented_evidence_matrix_key_and_missing_sentinel() -> None:
    source = pd.read_csv(
        DATA_ROOT
        / "files/analysis_ready/Supplementary_Data_1_full_evidence_matrix.csv",
        dtype=str,
        keep_default_na=False,
    )
    key = ["evidence_record_id", "analysis_window", "comparison_definition"]
    assert not source.duplicated(key).any()
    assert (source == "not_available").any().any()


def test_candidate_universe_records_post_result_selection_consistently() -> None:
    candidates = pd.read_csv(
        DATA_ROOT
        / "files/analysis_ready/Supplementary_Data_2_candidate_region_universe.csv",
        dtype=str,
        keep_default_na=False,
    )
    assert candidates.shape == (40, 23)
    assert not candidates["candidate_id"].duplicated().any()
    selected = candidates.loc[
        candidates["reporting_context"].eq("selected_exploratory_case")
    ]
    assert set(selected["candidate_id"]) == {
        "env_khor_fakkan_subregion",
        "pw_port561",
        "sar_khor_fakkan_adjacent",
    }
    assert selected["selection_timing"].eq("post_result_selected_case").all()
    strait = candidates.loc[candidates["candidate_id"].eq("pw_chokepoint6")]
    assert len(strait) == 1
    assert strait.iloc[0]["reporting_context"] == "regional_disruption_context"


def test_field_dictionary_matches_public_csv_schemas_and_units() -> None:
    dictionary = pd.read_csv(
        DATA_ROOT / "FIELD_DICTIONARY.csv", dtype=str, keep_default_na=False
    )
    declared = list(
        map(tuple, dictionary[["file", "field"]].itertuples(index=False, name=None))
    )
    actual: list[tuple[str, str]] = []
    for path in sorted((DATA_ROOT / "files").rglob("*.csv")):
        relative = path.relative_to(DATA_ROOT).as_posix()
        actual.extend((relative, field) for field in pd.read_csv(path, nrows=0).columns)
    assert len(declared) == len(set(declared))
    assert set(declared) == set(actual)

    indexed = dictionary.set_index(["file", "field"])
    assert indexed.loc[
        (
            "files/supplementary_figures/Supplementary_Figure_7_source_data.csv",
            "coverage_fraction",
        ),
        "storage_type",
    ] == "number"
    assert indexed.loc[
        (
            "files/analysis_ready/historical_pseudo_event.csv",
            "late_phase_no2_mean_population_coverage_fraction",
        ),
        "unit",
    ] == "fraction 0-1"
    assert indexed.loc[
        (
            "files/analysis_ready/khor_fakkan_late_phase_no2_alignment.csv",
            "no2_leave_march17_percent_change_from_primary_mean",
        ),
        "unit",
    ] == "%"
    sd1_semantics = dictionary.loc[
        dictionary["file"].eq(
            "files/analysis_ready/Supplementary_Data_1_full_evidence_matrix.csv"
        ),
        "missing_value_semantics",
    ]
    assert sd1_semantics.str.contains("not_available", regex=False).all()
    assert sd1_semantics.str.contains("zero remains an observed zero", regex=False).all()


def test_static_figure_provenance_is_public_and_resolvable() -> None:
    source = pd.read_csv(
        DATA_ROOT
        / "files/supplementary_figures/Supplementary_Figure_2_source_data.csv"
    )
    assert not source.astype(str).apply(
        lambda column: column.str.contains(r"[A-Za-z]:\\", regex=True).any()
    ).any()
    geometry_paths = source["public_geometry_path"].dropna().unique()
    assert len(geometry_paths) == 1
    assert (ROOT / geometry_paths[0]).is_file()
    assert source["official_catalogue_url"].str.startswith("https://").all()
    sar = source.loc[source["record_type"].eq("sar_patch")]
    assert sar["provider_product_id"].str.startswith("COPERNICUS/S1_GRD/").all()


def test_core_statistics_are_recomputed(tmp_path: Path) -> None:
    output = tmp_path / "statistics"
    result = reproduce_statistics(DATA_ROOT, output)
    assert result["status"] == "PASS"
    assert result["no2"]["status"] == "PASS"
    assert all(result["verification_against_shared_results"]["point_estimates"].values())
    assert all(result["verification_against_shared_results"]["bootstrap_contrasts"].values())
    assert all(
        result["no2"]["verification_against_shared_summary"]["numeric_fields"].values()
    )
    assert (output / "statistics/port_sar_year_summary.csv").is_file()
    assert (output / "statistics/port_sar_bootstrap.json").is_file()
    assert (output / "statistics/no2_may_june_summary.csv").is_file()
    assert (output / "statistics/no2_may_june_bootstrap.json").is_file()


def test_harmonized_no2_values_are_consistent_across_public_files() -> None:
    summary = pd.read_csv(
        DATA_ROOT / "files/statistical_inputs/no2_may_june_summary.csv",
        dtype=str,
        keep_default_na=False,
    )
    summary["buffer_key"] = summary["buffer_km"].astype(float)
    summary_keyed = {
        (row.analysis_id, float(row.buffer_km), row.phase): row
        for row in summary.itertuples(index=False)
    }
    numeric_fields = [
        "calendar_days_2026",
        "no2_valid_days_2026",
        "no2_mean_anomaly_mol_m2",
        "no2_equal_year_historical_mean_mol_m2",
        "no2_change_vs_historical_mol_m2",
        "no2_change_vs_historical_bootstrap_ci95_lower",
        "no2_change_vs_historical_bootstrap_ci95_upper",
        "no2_percent_change_vs_historical",
        "no2_percent_change_vs_historical_bootstrap_ci95_lower",
        "no2_percent_change_vs_historical_bootstrap_ci95_upper",
        "mean_population_coverage_fraction",
    ]

    figure_2 = pd.read_csv(
        DATA_ROOT / "files/main_figures/Figure_2_source_data.csv",
        dtype=str,
        keep_default_na=False,
    )
    assert figure_2.shape == (240, 78)
    assert not figure_2.duplicated().any()
    alignment = pd.read_csv(
        DATA_ROOT / "files/analysis_ready/khor_fakkan_late_phase_no2_alignment.csv",
        dtype=str,
        keep_default_na=False,
    )
    sfig_4 = pd.read_csv(
        DATA_ROOT
        / "files/supplementary_figures/Supplementary_Figure_4_source_data.csv",
        dtype=str,
        keep_default_na=False,
    )
    for key, expected in summary_keyed.items():
        analysis_id, buffer_km, phase = key
        for table in (figure_2, alignment):
            if (
                table is figure_2
                and analysis_id == "fujairah_khor_fakkan_east_coast_cluster"
            ):
                continue
            rows = table.loc[
                table["analysis_id"].eq(analysis_id)
                & pd.to_numeric(table["buffer_km"], errors="coerce").eq(buffer_km)
                & table["phase"].eq(phase)
            ]
            assert len(rows) == 1
            actual = rows.iloc[0]
            for field in numeric_fields:
                assert float(actual[field]) == pytest.approx(
                    float(getattr(expected, field)), rel=1e-10, abs=1e-15
                )
            assert json.loads(actual["historical_valid_days_by_year_json"]) == json.loads(
                expected.historical_valid_days_by_year_json
            )
        rows = sfig_4.loc[
            sfig_4["analysis_id"].eq(analysis_id)
            & pd.to_numeric(sfig_4["buffer_km"], errors="coerce").eq(buffer_km)
            & sfig_4["phase"].eq(phase)
        ]
        assert len(rows) == 1
        actual = rows.iloc[0]
        for field in (
            "no2_change_vs_historical_mol_m2",
            "no2_change_vs_historical_bootstrap_ci95_lower",
            "no2_change_vs_historical_bootstrap_ci95_upper",
        ):
            assert float(actual[field]) == pytest.approx(
                float(getattr(expected, field)), rel=1e-10, abs=1e-15
            )

    primary = summary_keyed[("khor_fakkan_subregion_sensitivity", 20.0, "late_phase")]
    historical = pd.read_csv(
        DATA_ROOT / "files/analysis_ready/historical_pseudo_event.csv",
        dtype=str,
        keep_default_na=False,
    )
    event_year = historical.loc[
        historical["year"].eq("2026")
        & historical["year_role"].eq("event_year")
        & historical["no2_analysis_id"].eq(primary.analysis_id)
        & pd.to_numeric(historical["no2_buffer_km"], errors="coerce").eq(
            float(primary.buffer_km)
        )
    ]
    assert len(event_year) == 1
    event_year = event_year.iloc[0]
    historical_field_map = {
        "late_phase_no2_calendar_days": "calendar_days_2026",
        "late_phase_no2_valid_days": "no2_valid_days_2026",
        "late_phase_no2_mean_mol_m2": "no2_mean_anomaly_mol_m2",
        "late_phase_no2_mean_population_coverage_fraction": "mean_population_coverage_fraction",
        "late_phase_no2_excluding_year_historical_reference_mean_mol_m2": "no2_equal_year_historical_mean_mol_m2",
        "late_phase_no2_change_vs_excluding_year_historical_reference_mol_m2": "no2_change_vs_historical_mol_m2",
        "late_phase_no2_percent_change_vs_excluding_year_historical_reference": "no2_percent_change_vs_historical",
    }
    for target_field, summary_field in historical_field_map.items():
        assert float(event_year[target_field]) == pytest.approx(
            float(getattr(primary, summary_field)), rel=1e-10, abs=1e-15
        )
    assert json.loads(event_year["no2_historical_reference_valid_days_json"]) == json.loads(
        primary.historical_valid_days_by_year_json
    )

    evidence = pd.read_csv(
        DATA_ROOT
        / "files/analysis_ready/Supplementary_Data_1_full_evidence_matrix.csv",
        dtype=str,
        keep_default_na=False,
    )
    evidence = evidence.loc[
        evidence["evidence_record_id"].eq("env_khor_fakkan_subregion")
        & evidence["analysis_region_id"].eq(primary.analysis_id)
        & evidence["analysis_window"].eq("late_phase_may01_to_jun30")
    ]
    assert len(evidence) == 1
    evidence = evidence.iloc[0]
    estimate = json.loads(evidence["estimate_in_original_unit"])
    context = json.loads(evidence["historical_context"])
    assert estimate["unit"] == "mol m-2"
    assert float(estimate["value"]) == pytest.approx(
        float(primary.no2_mean_anomaly_mol_m2), rel=1e-10, abs=1e-15
    )
    for target_field, summary_field in {
        "absolute_change": "no2_change_vs_historical_mol_m2",
        "relative_change": "no2_percent_change_vs_historical",
        "ci95_lower_in_reported_scale": "no2_change_vs_historical_bootstrap_ci95_lower",
        "ci95_upper_in_reported_scale": "no2_change_vs_historical_bootstrap_ci95_upper",
        "valid_days": "no2_valid_days_2026",
        "coverage_fraction": "mean_population_coverage_fraction",
    }.items():
        assert float(evidence[target_field]) == pytest.approx(
            float(getattr(primary, summary_field)), rel=1e-10, abs=1e-15
        )
    assert context["bootstrap_interval_excludes_zero"] is True
    assert float(context["historical_equal_year_mean"]) == pytest.approx(
        float(primary.no2_equal_year_historical_mean_mol_m2),
        rel=1e-10,
        abs=1e-15,
    )


def test_public_source_metadata_are_semantically_clean() -> None:
    evidence = pd.read_csv(
        DATA_ROOT
        / "files/analysis_ready/Supplementary_Data_1_full_evidence_matrix.csv",
        dtype=str,
        keep_default_na=False,
    )
    expected_domains = {
        "multipollutant_fingerprint_aai_": "buffer_mean_absorbing_aerosol_index",
        "multipollutant_fingerprint_aod_": "buffer_mean_aerosol_optical_depth",
        "multipollutant_fingerprint_co_": "buffer_mean_carbon_monoxide_total_column",
        "multipollutant_fingerprint_hcho_": "buffer_mean_tropospheric_formaldehyde_column",
        "multipollutant_fingerprint_nighttime_lights_": "buffer_mean_nighttime_lights_radiance",
        "multipollutant_fingerprint_no2_": "population_weighted_tropospheric_no2_column_anomaly",
        "multipollutant_fingerprint_so2_": "buffer_mean_sulfur_dioxide_column",
        "multipollutant_fingerprint_fixed_multipollutant_source_classification": "multipollutant_source_compatibility_classification",
    }
    expected_units = {
        "multipollutant_fingerprint_aai_": "valid_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_aod_": "valid_land_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_co_": "valid_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_hcho_": "valid_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_nighttime_lights_": "valid_land_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_no2_": "population_pixel_day_aggregated_to_region_fixed_window",
        "multipollutant_fingerprint_so2_": "valid_pixel_day_mean_aggregated_to_buffer_fixed_window",
        "multipollutant_fingerprint_fixed_multipollutant_source_classification": "region_fixed_window_source_compatibility_checklist",
    }
    matched = pd.Series(False, index=evidence.index)
    for prefix, expected_domain in expected_domains.items():
        rows = evidence["comparison_definition"].str.startswith(prefix)
        matched |= rows
        assert int(rows.sum()) == 45
        assert set(evidence.loc[rows, "measurement_domain"]) == {expected_domain}
        assert set(evidence.loc[rows, "statistical_unit"]) == {expected_units[prefix]}
    assert int(matched.sum()) == 360
    cross_domains = {
        "cross_region_event_study_cross_domain_decoupling_classification": (
            5,
            "cross_domain_decoupling_classification",
        ),
        "historical_pseudo_event_complete_six_item_and_late_phase_three_item_replication_summary": (
            1,
            "cross_domain_replication_summary",
        ),
    }
    for comparison, (expected_rows, expected_domain) in cross_domains.items():
        rows = evidence["comparison_definition"].eq(comparison)
        assert int(rows.sum()) == expected_rows
        assert set(evidence.loc[rows, "measurement_domain"]) == {expected_domain}

    def reject_constant(value: str) -> None:
        raise ValueError(value)

    for context in evidence["historical_context"]:
        if context in {"", "not_available"}:
            continue
        outer = json.loads(context, parse_constant=reject_constant)
        for key, value in outer.items():
            if key.endswith("_json") and isinstance(value, str) and value[:1] in "[{":
                json.loads(value, parse_constant=reject_constant)

    for name in (
        "Supplementary_Data_1_full_evidence_matrix.csv",
        "Supplementary_Data_2_candidate_region_universe.csv",
        "Supplementary_Data_3_baltimore_sar_scene_timeline.csv",
        "Supplementary_Data_4_baltimore_primary_differences.csv",
        "Supplementary_Data_5_acute_joint_extremeness.csv",
    ):
        table = pd.read_csv(
            DATA_ROOT / "files/analysis_ready" / name,
            dtype=str,
            keep_default_na=False,
        )
        assert not table.isin(["True", "False"]).any().any()

    figure_2 = pd.read_csv(
        DATA_ROOT / "files/main_figures/Figure_2_source_data.csv",
        dtype=str,
        keep_default_na=False,
    )
    assert figure_2.shape == (240, 78)
    assert not figure_2.eq("").all().any()
    assert not any(
        "burden" in column.lower() or "causal" in column.lower()
        for column in figure_2.columns
    )


def test_complete_lightweight_reproduction(tmp_path: Path) -> None:
    output = tmp_path / "reproduced"
    result = reproduce(DATA_ROOT, output)
    assert result["status"] == "LIGHTWEIGHT_REPRODUCTION_COMPLETE"
    assert len(result["figures"]) == 9
    assert len(result["supplementary_tables"]) == 10
    assert len(list((output / "figures").glob("*.pdf"))) == 8
    assert len(list((output / "figures").glob("*.svg"))) == 8
    assert len(list((output / "figures_600dpi").glob("*.png"))) == 8
    assert len(list((output / "supplementary_tables").glob("*.csv"))) == 10
    report = json.loads((output / "qa/REPRODUCIBILITY_REPORT.json").read_text(encoding="utf-8"))
    assert report["security_findings"] == []
    assert report["statistics"]["port_sar"]["status"] == "PASS"
    assert report["statistics"]["no2"]["status"] == "PASS"
    statuses = {row["figure"]: row["status"] for row in report["figure_output_inventory"]}
    assert statuses["Supplementary_Figure_2"] == "WITHHELD_PRE_ACCEPTANCE"
